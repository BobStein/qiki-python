"""
A qiki Word is defined by a three-word subject-verb-object
"""


import six
import time
import mysql.connector
from number import Number

class Word(object):
    """
    :type content: six.string_types | Word | instancemethod

    :type sbj: Number | Word
    :type vrb: Number | instancemethod
    :type obj: Number | Word
    :type num: Number
    :type txt: six.string_types

    :type _ID_DEFINE: Number
    :type _connection: mysql.connector.ySQLConnection
    """

    def __init__(self, content=None, sbj=None, vrb=None, obj=None, num=None, txt=None, table=None,connection=None):
        self._table = table
        self._connection = connection
        self.exists = False
        self.__id = None
        self._as_if_method = self.null_verb_method
        assert self._connection is not None, "Not connected, call Word.system()"
        if isinstance(content, six.string_types):
            self._from_definition(content)
        elif isinstance(content, Number):
            self._from_id(content)
        elif isinstance(content, type(self)):
            self._from_word(content)
        elif isinstance(content, type(self.define)):   # instancemethod
            # TODO: look up a vrb by its txt field being content.__name__
            pass
        elif content is None:
            self.sbj = sbj
            self.vrb = vrb
            self.obj = obj
            self.num = num
            self.txt = txt
        else:
            typename = type(content).__name__
            if typename == 'instance':
                pass#typename = content.__class__.__name__
            raise TypeError('Word(%s) is not supported' % typename)

    @classmethod
    def system(cls, **kwargs):
        service = kwargs.pop('service')
        assert service == 'MySQL'
        table = kwargs.pop('table')
        connection = mysql.connector.connect(**kwargs)
        # TODO:  Combine connection and table?  We could subclass like so:  Word.System(MySQLConnection)
        this_system = cls(cls._ID_SYSTEM, table=table, connection=connection)
        return this_system

    _ID_DEFINE = Number(1)
    _ID_NOUN   = Number(2)
    _ID_VERB   = Number(3)
    _ID_AGENT  = Number(4)
    _ID_SYSTEM = Number(5)

    _ID_MAX_FIXED = Number(5)

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
        define.__id = self._ID_DEFINE
        noun.__id = self._ID_NOUN
        verb.__id = self._ID_VERB
        agent.__id = self._ID_AGENT
        system.__id = self._ID_SYSTEM
        try:
            define.save()
            noun.save()
            verb.save()
            agent.save()
            system.save()
        except mysql.connector.IntegrityError:
            pass

    def uninstall_to_scratch(self):
        cursor = self._connection.cursor(prepared=True)
        cursor.execute("DELETE FROM `{table}`".format(table=self._table))
        cursor.close()

    def spawn(self, *args, **kwargs):
        """Word() for the same connection and table"""
        kwargs['table'] = self._table
        kwargs['connection'] = self._connection
        the_word = self.__class__(*args, **kwargs)
        return the_word

    def __call__(self, *args, **kwargs):
        if self.is_system():
            the_word = self.spawn(*args, **kwargs)
            assert the_word.exists
            assert the_word.sbj == self.id
            the_word._system = self
            return the_word
        else:
            assert self._system.exists and self._system.is_system()
            the_word = self._system.define(self, *args, **kwargs)
            the_word._system = self._system
            return the_word
        # elif self.is_a_noun():
        #     assert self._system.exists and self._system.is_system()
        #     the_word = self._system.define(self, *args, **kwargs)
        #     the_word._system = self._system
        #     return the_word
        # else:
        #     raise

        # In the case of person.like(obj), self points to like, not person.  There is no way to know person here.
        # This answer comes close:
        # http://stackoverflow.com/a/6575615/673991
        # But it assigns the child object to an instance of the parent class
        # I want it to work when the child is assigned to the parent class itself -- and to work for all past-or-future instantiations
        # print("HACK call " + self.txt)
        # return self._as_if_method(*args, **kwargs)

    def null_verb_method(self, *args, **kwargs):
        pass

    def noun(self, txt, num=Number(1)):
        return self.define(Word('noun'), txt, num)

    def define(self, obj, txt, num=Number(1)):
        already = self.spawn(txt)
        if already.exists:
            raise self.DefineDuplicateException("'{txt}' already defined, as a {obj_txt}.".format(
                txt=txt,
                obj_txt=self.spawn(already.obj).txt
            ))
        the_word = self.sentence(sbj=self, vrb=self.spawn('define'), obj=obj, txt=txt, num=num)
        return the_word

    def sentence(self, sbj, vrb, obj, txt, num):
        assert isinstance(sbj, Word), "sbj can't be a {type}".format(type=type(sbj).__name__)
        assert isinstance(vrb, Word), "vrb can't be a {type}".format(type=type(vrb).__name__)
        assert isinstance(obj, Word), "obj can't be a {type}".format(type=type(obj).__name__)
        assert isinstance(txt, six.string_types)
        assert isinstance(num, Number)
        word_object = self.spawn(sbj=sbj.id, vrb=vrb.id, obj=obj.id, num=num, txt=txt)
        # if word_object.is_a(Word('verb')):
        #     def verb_method(_self, _obj, _txt, _num=Number(1)):
        #         verb_object = _self.define(_obj, txt=_txt, num=_num, vrb_txt=word_object.txt)   # freaky how word_object works here
        #         return verb_object
        #     word_object._as_if_method = verb_method
        word_object.save()
        return word_object

    @classmethod
    def make_verb_a_method(cls, verb):
        setattr(cls, verb.txt, verb)

    def disconnect(self):
        self._connection.close()

    def _from_id(self, _id):
        """Construct a Word from its id
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
        """Construct a Word from its txt"""
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
            if parent.vrb == self._ID_DEFINE and parent.obj == word.id:
                return True
        return False

    def is_a_noun(self):
        return self.is_a(self.spawn('noun'))

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
        sbj = Word(self.sbj)
        vrb = Word(self.vrb)
        obj = Word(self.obj)
        return "{sbj}.{vrb}({obj}, {txt}{maybe_num})".format(
            sbj=sbj.txt,
            vrb=vrb.txt,
            obj=obj.txt,
            txt=repr(self.txt),
            maybe_num=(", " + str(self.num)) if self.num != 1 else "",
        )

    @staticmethod
    def number_from_mysql(mysql_blob):
        return Number.from_raw(six.binary_type(mysql_blob))

    @property
    def id(self):
        return self.__id

    @id.setter
    def id(self, value):
        raise RuntimeError("Cannot set a Word's id")

    def __repr__(self):
        if hasattr(self, 'txt'):
            return "Word('{0}')".format(self.txt)
        elif hasattr(self, '__id'):
            return "Word(Number('{id_qstring}'))".format(qstring=self.id.qstring())

    def max_id(self):
        cursor = self._connection.cursor()
        cursor.execute("SELECT MAX(id) FROM `{table}`".format(table=self._table))
        return self.number_from_mysql(cursor.fetchone()[0])

    def save(self):
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


# TODO: don't raise built-in classes, raise subclasses of built-in exceptions
# TODO: Word attributes sbj,vrb,obj might be more convenient as Words, not Numbers.
# ...If so they'd need to be dynamic properties -- and avoid infinite recursion!
# ...One way to do this might be x = Word(id) wouldn't generate database activity
# ......unless some other method were called, e.g. x.vrb
# TODO: Singleton pattern, so e.g. Word('noun') is Word('noun')