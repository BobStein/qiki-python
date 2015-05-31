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
        assert self._connection is not None, "Call Word.connect(database credentials)"
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
        define = Word(
            sbj = self._ID_SYSTEM,
            vrb = self._ID_DEFINE,
            obj = self._ID_VERB,
            num = Number(1),
            txt = u'define',
            connection=self._connection,
            table=self._table,
        )
        noun = Word(
            sbj = self._ID_SYSTEM,
            vrb = self._ID_DEFINE,
            obj = self._ID_NOUN,
            num = Number(1),
            txt = u'noun',
            connection=self._connection,
            table=self._table,
        )
        verb = Word(
            sbj = self._ID_SYSTEM,
            vrb = self._ID_DEFINE,
            obj = self._ID_NOUN,
            num = Number(1),
            txt = u'verb',
            connection=self._connection,
            table=self._table,
        )
        agent = Word(
            sbj = self._ID_SYSTEM,
            vrb = self._ID_DEFINE,
            obj = self._ID_NOUN,
            num = Number(1),
            txt = u'agent',
            connection=self._connection,
            table=self._table,
        )
        system = Word(
            sbj = self._ID_SYSTEM,
            vrb = self._ID_DEFINE,
            obj = self._ID_AGENT,
            num = Number(1),
            txt = u'system',
            connection=self._connection,
            table=self._table,
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

    def __call__(self, *args, **kwargs):
        kwargs['table'] = self._table
        kwargs['connection'] = self._connection
        the_word = self.__class__(*args, **kwargs)
        if the_word.exists:
            return the_word
        else:
            raise

        # In the case of person.like(obj), self points to like, not person.  There is no way to know person here.
        # This answer comes close:
        # http://stackoverflow.com/a/6575615/673991
        # But it assigns the child object to an instance of the parent class
        # I want it to work when the child is assigned to the parent class itself -- and to work for all past-or-future instantiations
        print("HACK call " + self.txt)
        return self._as_if_method(*args, **kwargs)

    def null_verb_method(self, *args, **kwargs):
        pass

    def noun(self, txt, num=Number(1)):
        return self.define(Word('noun'), txt, num)

    def define(self, obj, txt, num=Number(1)):
        self.sentence(self, vrb, obj)

    def sentence(self, sbj, vrb, obj, txt, num):
        assert isinstance(obj, Word), "obj can't be a {type}".format(type=type(obj).__name__)
        assert isinstance(txt, six.string_types)
        assert isinstance(num, Number)
        assert isinstance(vrb_txt, six.string_types)
        if Word(txt).exists:
            raise self.DefineDuplicateException
        word_object = Word(sbj=self.id, vrb=Word(vrb_txt).id, obj=obj.id, num=num, txt=txt)
        if word_object.is_a(Word('verb')):
            def verb_method(_self, _obj, _txt, _num=Number(1)):
                verb_object = _self.define(_obj, txt=_txt, num=_num, vrb_txt=word_object.txt)   # freaky how word_object works here
                return verb_object
            word_object._as_if_method = verb_method
        word_object.save()
        return word_object

    @classmethod
    def make_verb_a_method(cls, verb):
        setattr(cls, verb.txt, verb)

    def __getattr__(self, item):
        print("Word get {item}".format(item=item))

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
        return self.vrb == self._ID_DEFINE and self.obj == word.id

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

    @classmethod
    def max_id(cls):
        cursor = cls._connection.cursor()
        cursor.execute("SELECT MAX(id) FROM `{table}`".format(table=cls._table))
        return cls.number_from_mysql(cursor.fetchone()[0])

    def save(self):
        assert isinstance(self.__id, (Number, type(None)))
        assert isinstance(self.sbj, Number)
        assert isinstance(self.vrb, Number)
        assert isinstance(self.obj, Number)
        assert isinstance(self.num, Number)
        assert isinstance(self.txt, six.string_types)
        assert not self.exists
        _id = self.__id
        if _id is None:
            _id = self.max_id().inc()   # AUTO sorta INCREMENT
        assert isinstance(_id, Number)
        cursor = self._connection.cursor(prepared=True)
        cursor.execute(
            "INSERT INTO `{table}` "
            "       (  `id`,    `sbj`,    `vrb`,    `obj`,    `num`, `txt`,   `whn`) "
            "VALUES (x'{id}', x'{sbj}', x'{vrb}', x'{obj}', x'{num}',    ?, x'{whn}')"
            .format(
                table=self._table,
                id=_id.hex(),
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
    class DefineDuplicateException:
        pass


# TODO: raise subclass of built-in exceptions
