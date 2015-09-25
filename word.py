"""
A qiki Word is defined by a three-word subject-verb-object
"""

from __future__ import print_function
import re
import time

import mysql.connector
import six

from number import Number


class Word(object):
    """
    A qiki Word is a subject-verb-object triplet of other words.

    A word is identified by a qiki Number id.
    A word may be elaborated by a number and some text.
    A word remembers the time it was created.

    :type content: six.string_types | Word | instancemethod

    :type sbj: Number | Word
    :type vrb: Number | instancemethod
    :type obj: Number | Word
    :type num: Number
    :type txt: six.string_types

    :type _connection: mysql.connector.MySQLConnection
    :type _table": six.string_types
    :type _system": Word
    """

    def __init__(self, content=None, sbj=None, vrb=None, obj=None, num=None, txt=None, table=None, connection=None):
        self._table = table
        self._connection = connection
        self.exists = False
        self.__id = None
        self._as_if_method = self.null_verb_method
        if isinstance(content, six.string_types):
            assert isinstance(self._connection, mysql.connector.MySQLConnection), "Not connected."
            self._from_definition(content)
        elif isinstance(content, Number):
            assert isinstance(self._connection, mysql.connector.MySQLConnection), "Not connected."
            self._from_id(content)
        elif isinstance(content, type(self)):
            assert isinstance(self._connection, mysql.connector.MySQLConnection), "Not connected."
            self._from_word(content)
        elif content is None:
            self.sbj = sbj
            self.vrb = vrb
            self.obj = obj
            self.num = num
            self.txt = txt
        else:
            typename = type(content).__name__
            if typename == 'instance':
                typename = content.__class__.__name__
            raise TypeError('Word(%s) is not supported' % typename)

    _ID_DEFINE = Number(1)
    _ID_NOUN   = Number(2)
    _ID_VERB   = Number(3)
    _ID_AGENT  = Number(4)
    _ID_SYSTEM = Number(5)

    _ID_MAX_FIXED = Number(5)

    def __getattr__(self, item):
        assert hasattr(self, '_system')
        return_value = self._system(item)
        return_value._meta_self = self
        return return_value

    def __call__(self, *args, **kwargs):
        if self.is_system():   # system('name')
            assert self.id == self._ID_SYSTEM
            existing_word = self.spawn(*args, **kwargs)
            assert existing_word.exists, "There is no {name}".format(name=repr(args[0]))
            if existing_word.id == self.id:
                return self   # system is a singleton
            return existing_word
        elif self.is_a_verb(reflexive=False):   # subject.verb(object, ...)
            assert hasattr(self, '_system')
            assert self._system.exists
            assert self._system.is_system()

            # TODO:  keyword-only or flexible positional arguments?
            # https://www.python.org/dev/peps/pep-3102/
            # http://code.activestate.com/recipes/577940-emulate-keyword-only-arguments-in-python-2/

            # DONE:  s.v(o)

            # TODO:  disallow positional arguments?
            # DONE:  s.v(o,n)
            # TODO:  s.v(o,t)
            # DONE:  s.v(o,n,t)
            # TODO:  s.v(o,t,n)

            # TODO:  support keyword arguments:
            # TODO:  s.v(o,num=n)
            # TODO:  s.v(o,txt=t)
            # TODO:  s.v(o,num=n,txt=t)
            # TODO:  s.v(o,txt=t,num=n)

            assert len(args) >= 1
            obj = args[0]
            try:
                num = Number(args[1])
            except IndexError:
                num = Number(1)
            try:
                txt = args[2]
            except IndexError:
                txt=''
            assert hasattr(self, '_meta_self')
            if len(args) == 1:
                existing_word = self._system.spawn(sbj=self._meta_self.id, vrb=self.id, obj=obj.id)
                existing_word.lookup_svo()
                assert existing_word.exists
            else:
                existing_word = self.sentence(sbj=self._meta_self, vrb=self, obj=obj, num=num, txt=txt)
            return existing_word
        elif self.is_definition():   # subject.noun('name')
            assert hasattr(self, '_system')
            assert self._system.exists
            assert self._system.is_system()
            existing_or_new_word = self._system.define(self, *args, **kwargs)
            return existing_or_new_word
        else:
            raise self.NonVerbUndefinedAsFunctionException(
                "Word {_id} cannot be used as a function -- it's neither a verb nor a definition.".format(
                    _id=int(self.id)
                )
            )

    def null_verb_method(self, *args, **kwargs):
        pass

    def define(self, obj, txt, num=Number(1)):
        existing_word = self.spawn(txt)
        if existing_word.exists:
            return existing_word
        new_word = self.sentence(sbj=self, vrb=self('define'), obj=obj, txt=txt, num=num)
        return new_word

    def spawn(self, *args, **kwargs):
        """
        Construct a Word() using the same _connection, _table, and _system.

        The word may exist already.  Otherwise it will be prepared to .save().
        """
        kwargs['table']      = self._table
        kwargs['connection'] = self._connection
        the_word = Word(*args, **kwargs)
        assert hasattr(self, '_system')
        the_word._system = self._system
        return the_word

    def sentence(self, sbj, vrb, obj, txt, num):
        assert isinstance(sbj, Word),             "sbj cannot be a {type}".format(type=type(sbj).__name__)
        assert isinstance(vrb, Word),             "vrb cannot be a {type}".format(type=type(vrb).__name__)
        assert isinstance(obj, Word),             "obj cannot be a {type}".format(type=type(obj).__name__)
        assert isinstance(txt, six.string_types), "txt cannot be a {type}".format(type=type(txt).__name__)
        assert isinstance(num, Number),           "num cannot be a {type}".format(type=type(num).__name__)
        new_word = self.spawn(sbj=sbj.id, vrb=vrb.id, obj=obj.id, num=num, txt=txt)
        new_word.save()
        return new_word

    @classmethod
    def make_verb_a_method(cls, verb):
        setattr(cls, verb.txt, verb)

    def disconnect(self):
        self._connection.close()

    def _from_id(self, _id):
        """
        Construct a Word from its id.

        :type _id: Number
        """
        assert isinstance(_id, Number)
        self._load_row(
            "SELECT * FROM `{table}` WHERE `id` = ?"
            .format(
                table=self._table,
            ),
            (
                _id.raw,
            )
        )

    def _from_definition(self, txt):
        """Construct a Word from its txt, but only when it's a definition."""
        assert isinstance(txt, six.string_types)
        self._load_row(
            "SELECT * FROM `{table}` "
                "WHERE   `vrb` = ? "
                    "AND `txt` = ?"
            .format(
                table=self._table,
            ),
            (
                self._ID_DEFINE.raw,
                txt
            )
        )
        if not self.exists:
            self.txt = txt

    def _from_word(self, word):
        if word.exists:
            self._from_id(word.id)
        else:
            self._from_definition(word.txt)

    def lookup_svo(self):
        assert isinstance(self.sbj, Number)
        assert isinstance(self.vrb, Number)
        assert isinstance(self.obj, Number)
        self._load_row(
            "SELECT * FROM `{table}` "
                "WHERE   `sbj` = ? "
                    "AND `vrb` = ? "
                    "AND `obj` = ? "
                "ORDER BY `id` DESC "
                "LIMIT 1"
            .format(
                table=self._table,
            ),
            (
                self.sbj.raw,
                self.vrb.raw,
                self.obj.raw,
            )
        )

    def _load_row(self, sql, params=()):
        cursor = self._connection.cursor(prepared=True)
        cursor.execute(sql, params)
        tuple_row = cursor.fetchone()
        if tuple_row is not None:
            self.exists = True
            dict_row = dict(zip(cursor.column_names, tuple_row))
            self.__id = Number.from_mysql(dict_row['id'])
            self.sbj = Number.from_mysql(dict_row['sbj'])
            self.vrb = Number.from_mysql(dict_row['vrb'])
            self.obj = Number.from_mysql(dict_row['obj'])
            self.num = Number.from_mysql(dict_row['num'])
            self.txt = str(dict_row['txt'].decode('utf-8'))   # http://stackoverflow.com/q/27566078/673991
        cursor.close()

    def is_a(self, word, reflexive=True, recursion=10):
        assert recursion >= 0
        if reflexive and self.id == word.id:
            return True
        if recursion <= 0:
            return False
        if self.vrb != self._ID_DEFINE:
            return False
        if self.obj == word.id:
            return True
        parent = self.spawn(self.obj)
        if parent.id == self.id:
            return False
        return parent.is_a(word, reflexive=reflexive, recursion=recursion-1)   # TODO: limit recursion

    def is_a_noun(self, reflexive=True, **kwargs):
        assert hasattr(self, '_system')
        return self.is_a(self._system.noun, reflexive=reflexive, **kwargs)

    def is_a_verb(self, reflexive=False, **kwargs):
        assert hasattr(self, '_system')
        return self.is_a(self._system.verb, reflexive=reflexive, **kwargs)

    def is_define(self):
        return self.id == self._ID_DEFINE

    def is_definition(self):
        return self.vrb == self._ID_DEFINE

    def is_noun(self):
        return self.id == self._ID_NOUN

    def is_verb(self):
        return self.id == self._ID_VERB

    def is_agent(self):
        return self.id == self._ID_AGENT

    def is_system(self):
        return self.id == self._ID_SYSTEM

    def description(self):
        sbj = self.spawn(self.sbj)
        vrb = self.spawn(self.vrb)
        obj = self.spawn(self.obj)
        return "{sbj}.{vrb}({obj}, {num}{maybe_txt})".format(
            sbj=sbj.txt,
            vrb=vrb.txt,
            obj=obj.txt,
            num=self.presentable(self.num),
            maybe_txt=(", " + repr(self.txt)) if self.txt != '' else "",
        )

    @staticmethod
    def presentable(num):
        if num.is_whole():
            return str(int(num))
        else:
            return str(float(num))

    def __repr__(self):
        if hasattr(self, 'txt') and self.is_definition():
            return "Word('{0}')".format(self.txt)
        elif self.exists:
            return "Word(Number({id_qstring}))".format(id_qstring=self.id.qstring())
        else:
            return("Word(sbj={sbj}, vrb={vrb}, obj={obj}, txt={txt}, num={num})".format(
                sbj=self.sbj.qstring(),
                vrb=self.vrb.qstring(),
                obj=self.obj.qstring(),
                txt=repr(self.txt),
                num=self.num.qstring(),
            ))

    @property
    def id(self):
        return self.__id

    @id.setter
    def id(self, value):
        raise RuntimeError("Cannot set a Word's id")

    def max_id(self):
        cursor = self._connection.cursor()
        cursor.execute("SELECT MAX(id) FROM `{table}`".format(table=self._table))
        max_id_sql_row = cursor.fetchone()
        if max_id_sql_row is None:
            return Number(0)
        max_id_sql = max_id_sql_row[0]
        if max_id_sql is None:
            return Number(0)
        return Number.from_mysql(max_id_sql)

    def save(self, override_id=None):
        if override_id is not None:
            self.__id = override_id
        assert isinstance(self.__id, (Number, type(None)))
        assert isinstance(self.sbj, Number)
        assert isinstance(self.vrb, Number)
        assert isinstance(self.obj, Number), "{obj} is not a Number".format(obj=repr(self.obj))
        assert isinstance(self.num, Number)
        assert isinstance(self.txt, six.string_types)
        assert not self.exists
        if self.__id is None:
            self.__id = self.max_id().inc()   # AUTO sorta INCREMENT
        assert isinstance(self.__id, Number)
        # TODO: named substitutions with NON-prepared statements??
        # https://dev.mysql.com/doc/connector-python/en/connector-python-api-mysqlcursor-execute.html
        # http://stackoverflow.com/questions/1947750/does-python-support-mysql-prepared-statements/31979062#31979062
        cursor = self._connection.cursor(prepared=True)
        cursor.execute(
            "INSERT INTO `{table}` "
                   "(id, sbj, vrb, obj, num, txt, whn) "
            "VALUES ( ?,   ?,   ?,   ?,   ?,   ?,   ?)"
            .format(
                table=self._table,
            ),
            (
                self.__id.raw,
                self.sbj.raw,
                self.vrb.raw,
                self.obj.raw,
                self.num.raw,
                self.txt,
                Number(time.time()).raw,
            )
        )
        self._connection.commit()
        self.exists = True
        cursor.close()

    # noinspection PyClassHasNoInit
    class DefineDuplicateException(Exception):
        pass

    # noinspection PyClassHasNoInit
    class NonVerbUndefinedAsFunctionException(Exception):
        pass

    def get_all_ids(self):
        cursor = self._connection.cursor()
        cursor.execute("SELECT id FROM `{table}` ORDER BY id ASC".format(table=self._table))
        ids = []
        for row in cursor:
            _id = Number.from_mysql(row[0])
            ids.append(_id)
        cursor.close()
        return ids


class System(Word):   # rename candidates:  Site, Book, Server, Domain, Dictionary, Qorld, Booq, Lex,
                      #                     Station, Repo, Repository, Depot, Log, Tome, Manuscript, Diary,
                      #                     Heap, Midden, Scribe,
                      # Eventually, this will encapsulate other word repositories

    def __init__(self, **kwargs):
        language = kwargs.pop('language')
        assert language == 'MySQL'
        table = kwargs.pop('table')
        connection = mysql.connector.connect(**kwargs)
        self._system = self
        # TODO:  Combine connection and table?  We could subclass like so:  System(MySQLConnection)
        # TODO:  ...No, make them properties of System.  And make all Words refer to a System
        # TODO:  ...So combine all three.  Maybe System shouldn't subclass Word?
        try:
            super(self.__class__, self).__init__(self._ID_SYSTEM, table=table, connection=connection)
        except mysql.connector.ProgrammingError as exception:
            exception_message = str(exception)
            if re.search(r"Table .* doesn't exist", exception_message):
                self.install_from_scratch()   # TODO: Don't install twice, don't super() twice -- not D.R.Y.
                super(self.__class__, self).__init__(self._ID_SYSTEM, table=table, connection=connection)
            else:
                assert False, exception_message

        self._seminal_word(self._ID_DEFINE, self._ID_VERB, u'define')
        self._seminal_word(self._ID_NOUN, self._ID_NOUN, u'noun')
        self._seminal_word(self._ID_VERB, self._ID_NOUN, u'verb')
        self._seminal_word(self._ID_AGENT, self._ID_NOUN, u'agent')
        self._seminal_word(self._ID_SYSTEM, self._ID_AGENT, u'system')

        if not self.exists:
            self._from_id(self._ID_SYSTEM)
        assert self.exists

        assert self.is_system()
        assert self._connection.is_connected()

    def install_from_scratch(self):
        cursor = self._connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS `{table}` (
                `id` varbinary(255) NOT NULL,
                `sbj` varbinary(255) NOT NULL,
                `vrb` varbinary(255) NOT NULL,
                `obj` varbinary(255) NOT NULL,
                `num` varbinary(255) NOT NULL,
                `txt` varchar(255) NOT NULL,
                `whn` varbinary(255) NOT NULL,
                PRIMARY KEY (`id`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8;
        """.format(table=self._table))
        # TODO: other keys?  sbj-vrb?   obj-vrb?
        cursor.close()

    mysql.connector
    def _seminal_word(self, _id, _obj, _txt):
        word = Word(_id, table=self._table, connection=self._connection)
        if not word.exists:
            print("Installing word", _txt)
            self._install_word(_id, _obj, _txt)
            word = Word(_id, table=self._table, connection=self._connection)
        assert word.exists

    def _install_word(self, _id, _obj, _txt):
        word = self.spawn(
            sbj = self._ID_SYSTEM,
            vrb = self._ID_DEFINE,
            obj = _obj,
            num = Number(1),
            txt = _txt,
        )
        try:
            word.save(override_id=_id)
        except mysql.connector.IntegrityError:
            # TODO:  What was I thinking should happen here?
            raise
        except mysql.connector.ProgrammingError as exception:
            exception_message = str(exception)
            if re.search(r"INSERT command denied to user", exception_message):
                print("GRANT INSERT ON db TO user@host?")
                raise
            else:
                print(exception_message)
                raise

    def uninstall_to_scratch(self):
        cursor = self._connection.cursor(prepared=True)
        try:
            cursor.execute("DELETE FROM `{table}`".format(table=self._table))
        except mysql.connector.ProgrammingError:
            pass
        cursor.execute("DROP TABLE IF EXISTS `{table}`".format(table=self._table))
        cursor.close()


# TODO: Do not raise built-in classes, raise subclasses of built-in exceptions
# TODO: Word attributes sbj,vrb,obj might be more convenient as Words, not Numbers.
# TODO: ...If so they would need to be dynamic properties -- and avoid infinite recursion!
# TODO: ...One way to do this might be x = Word(id) would not generate database activity
# TODO: ......unless some other method were called, e.g. x.vrb
# TODO: Singleton pattern, so e.g. Word('noun') is Word('noun')
# TODO: Logging callback
