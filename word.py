"""
A qiki Word is defined by a three-word subject-verb-object
"""


import six
import time
import mysql.connector
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
        if self.is_system():
            assert self.id == self._ID_SYSTEM
            existing_word = self.spawn(*args, **kwargs)
            assert existing_word.exists, "There is no {name}".format(name=repr(args[0]))
            return existing_word
        elif self.is_a_verb():
            assert hasattr(self, '_system')
            assert self._system.exists
            assert self._system.is_system()
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
        else:
            assert hasattr(self, '_system')
            assert self._system.exists
            assert self._system.is_system()
            existing_or_new_word = self._system.define(self, *args, **kwargs)
            return existing_or_new_word

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
        assert isinstance(sbj, Word),             "sbj can't be a {type}".format(type=type(sbj).__name__)
        assert isinstance(vrb, Word),             "vrb can't be a {type}".format(type=type(vrb).__name__)
        assert isinstance(obj, Word),             "obj can't be a {type}".format(type=type(obj).__name__)
        assert isinstance(txt, six.string_types), "txt can't be a {type}".format(type=type(txt).__name__)
        assert isinstance(num, Number),           "num can't be a {type}".format(type=type(num).__name__)
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
            "SELECT * FROM `{table}` WHERE `id` = x'{id}'"
            .format(
                table=self._table,
                id=_id.hex(),
            )
        )

    def _from_definition(self, txt):
        """Construct a Word from its txt, but only when it's a definition."""
        assert isinstance(txt, six.string_types)
        self._load_row(
            "SELECT * FROM `{table}` WHERE `vrb` = x'{define}' AND `txt` = ?"
            .format(
                table=self._table,
                define=self._ID_DEFINE.hex(),
            ),
            (txt,)
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
            "SELECT * "
                "FROM `{table}` "
                "WHERE `sbj` = x'{sbj}' "
                    "AND `vrb` = x'{vrb}' "
                    "AND `obj` = x'{obj}' "
                "ORDER BY `id` DESC "
                "LIMIT 1"
            .format(
                table=self._table,
                sbj=self.sbj.hex(),
                vrb=self.vrb.hex(),
                obj=self.obj.hex(),
            ),
        )

    def _load_row(self, sql, params=()):
        cursor = self._connection.cursor(prepared=True)
        cursor.execute(sql, params)
        tuple_row = cursor.fetchone()
        if tuple_row is not None:
            self.exists = True
            dict_row = dict(zip(cursor.column_names, tuple_row))
            self.__id = self.number_from_mysql(dict_row['id'])
            self.sbj = self.number_from_mysql(dict_row['sbj'])
            self.vrb = self.number_from_mysql(dict_row['vrb'])
            self.obj = self.number_from_mysql(dict_row['obj'])
            self.num = self.number_from_mysql(dict_row['num'])
            self.txt = str(dict_row['txt'].decode('utf-8'))   # http://stackoverflow.com/q/27566078/673991
        cursor.close()

    def is_a(self, word):
        if self.vrb == self._ID_DEFINE:
            if self.obj == word.id:
                return True
            parent = self.spawn(self.obj)
            if parent.id == self.id:
                return False
            return parent.is_a(word)
        return False

    def is_a_noun(self):
        assert hasattr(self, '_system')
        return self.is_a(self._system.noun)

    def is_a_verb(self):
        assert hasattr(self, '_system')
        return self.is_a(self._system.verb)

    def is_define(self):
        return self.id == self._ID_DEFINE

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
        return "{sbj}.{vrb}({obj}{maybe_num}{maybe_txt})".format(
            sbj=sbj.txt,
            vrb=vrb.txt,
            obj=obj.txt,
            maybe_num=(", " + self.presentable(self.num)) if self.num != 1 else "",
            maybe_txt=(", " + repr(self.txt)) if self.txt != '' else "",
        )

    @staticmethod
    def presentable(num):
        if num.is_whole():
            return str(int(num))
        else:
            return str(float(num))

    def __repr__(self):
        if hasattr(self, 'txt') and self.spawn(self.vrb).is_define():
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

    @staticmethod
    def number_from_mysql(mysql_blob):
        return Number.from_raw(six.binary_type(mysql_blob))

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
        return self.number_from_mysql(max_id_sql)

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
        cursor = self._connection.cursor(prepared=True)
        cursor.execute(
            "INSERT INTO `{table}` "
            "       (  `id`,    `sbj`,    `vrb`,    `obj`,    `num`, `txt`,   `whn`) "
            "VALUES (x'{id}', x'{sbj}', x'{vrb}', x'{obj}', x'{num}',    ?, x'{whn}')"
            .format(
                table=self._table,
                id=self.__id.hex(),
                sbj=self.sbj.hex(),
                vrb=self.vrb.hex(),
                obj=self.obj.hex(),
                num=self.num.hex(),
                whn=Number(time.time()).hex(),
            ),
            (self.txt, )
        )
        self._connection.commit()
        self.exists = True
        cursor.close()

    # noinspection PyClassHasNoInit
    class DefineDuplicateException(Exception):
        pass

    def get_all_ids(self):
        cursor = self._connection.cursor()
        cursor.execute("SELECT id FROM `{table}` ORDER BY id ASC".format(table=self._table))
        ids = []
        for row in cursor:
            _id = self.number_from_mysql(row[0])
            ids.append(_id)
        return ids


class System(Word):

    def __init__(self, **kwargs):
        service = kwargs.pop('service')
        assert service == 'MySQL'
        table = kwargs.pop('table')
        connection = mysql.connector.connect(**kwargs)
        # TODO:  Combine connection and table?  We could subclass like so:  System(MySQLConnection)
        # TODO:  No, make them properties of System.  And make all Words refer to a System
        # TODO:  So combine all three.  Maybe System shouldn't subclass Word?
        super(self.__class__, self).__init__(self._ID_SYSTEM, table=table, connection=connection)
        self._system = self

    def install_from_scratch(self):
        self.uninstall_to_scratch()
        define = self.spawn(
            sbj = self._ID_SYSTEM,
            vrb = self._ID_DEFINE,
            obj = self._ID_VERB,
            num = Number(1),
            txt = u'define',
        )
        noun = self.spawn(
            sbj = self._ID_SYSTEM,
            vrb = self._ID_DEFINE,
            obj = self._ID_NOUN,
            num = Number(1),
            txt = u'noun',
        )
        verb = self.spawn(
            sbj = self._ID_SYSTEM,
            vrb = self._ID_DEFINE,
            obj = self._ID_NOUN,
            num = Number(1),
            txt = u'verb',
        )
        agent = self.spawn(
            sbj = self._ID_SYSTEM,
            vrb = self._ID_DEFINE,
            obj = self._ID_NOUN,
            num = Number(1),
            txt = u'agent',
        )
        system = self.spawn(
            sbj = self._ID_SYSTEM,
            vrb = self._ID_DEFINE,
            obj = self._ID_AGENT,
            num = Number(1),
            txt = u'system',
        )
        try:
            define.save(override_id=self._ID_DEFINE)
            noun.save(override_id=self._ID_NOUN)
            verb.save(override_id=self._ID_VERB)
            agent.save(override_id=self._ID_AGENT)
            system.save(override_id=self._ID_SYSTEM)
        except mysql.connector.IntegrityError:
            raise

    def uninstall_to_scratch(self):
        cursor = self._connection.cursor(prepared=True)
        cursor.execute("DELETE FROM `{table}`".format(table=self._table))
        cursor.close()


# TODO: don't raise built-in classes, raise subclasses of built-in exceptions
# TODO: Word attributes sbj,vrb,obj might be more convenient as Words, not Numbers.
# ...If so they'd need to be dynamic properties -- and avoid infinite recursion!
# ...One way to do this might be x = Word(id) wouldn't generate database activity
# ......unless some other method were called, e.g. x.vrb
# TODO: Singleton pattern, so e.g. Word('noun') is Word('noun')