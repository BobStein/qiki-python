# qiki -- rate anything

A qiki is part of a no-center public record 
of what anybody thinks of anything.
Including what we think of each other's thinking.
And what we think of each other.
Crazy, right?


## get good

The best opportunity for human betterment today
is to get good at deciding:

1. what **is**
2. what **ought** to be
3. what to **do** about it

Let's get better at these.
Many great consequences are held back until we do.
We don't need to agree.
But we do have decisions to make, 
and move on,
in a way most everyone can get behind.

Impossible you think?
I'm not so sure.
I am sure if we don't figure this out
it will ruin us.
I think someone's going to figure it out,
how to resolve as a group.
I'd rather it be us.
I'd rather it be humans
than some species living on our ruins.

We must find a way to decide 
what is **happening**.
This is why many discussions 
talk past each other.
We need some agreement on what is happening
before we can talk about what **matters**.
We need enough agreement on what matters
before we can talk about what to **do**.

Who is we?
This applies to any group you can think of.
The opportunity is overripe
for getting better at group decisions.


## how

I think the gizmos can help us out.
Start by storing our thinking 
outside the big tech silos.
Then anybody can begin looking for patterns.
And turning the gizmos loose looking for patterns.
And looking for meaning.
The time to create value and safety
by obscuring will soon be over.
It is time to put all our thinking on the table.

A qiki will allow you to rate and relate:

* anything you can see or say 
(not just what you're shown or told)
* to any degree
(some things matter more than others)
* with any verb 
(not just likes and wows)
* explanations welcome
(the world wants your fresh thinking)

Rate the ratings. 
Rate the raters. 
It's everyone's job to have opinions.
And everyone's job to figure out what they mean.

No company is powerful enough, 
no government is rich enough,
no review staff is responsible enough --
no subset has enough smarts --
to decide the most important decisions.
Or decide who decides them.
This has got to be everyone's job.
Yes it's going to be very hard. 

This is how we'll get big things done
without being overwhelmed, 
without losing our minds,
or our humanity 
(or whatever divinity means to you):
by teaching machines to 
tease out of many opinions 
what we want,
what actually matters to us.

If you don't think machines are up to that
you're probably right.
We need better machines 
and better machine teachers. 
But before we start those negotiations
we need a rich collection of opinions
out in the open.
Let's get started.

((some kind of smooth transition 
to some technical stuff goes here))


## word

A qiki word, like a natural language word, 
can represent anything.
Unlike a natural language word 
you can make up a lot of them easily.

When you make up a new qiki word 
you string together three other qiki words:

* subject
* verb
* object

and you give the new word a number
and some text:

* number 
(1 means normal, 
2 means you mean it twice as much.
Numbers are awesome.
They can be tiny, they can be huge.
And you get to say what they mean)
* text 
(because you've got a lot of splainin to do)

and store this in a lex. 


## lex

A lex is a dictionary for your made-up words.
For each word, a lex will remember:

* id number
* when you defined it

So that's 7 parts to a word. 
Here's what they're called:

* `sbj` - subject 
* `vrb` - verb
* `obj` - object
* `num` - quantify matters
* `txt` - name, explain, discuss, UTF-8
* `idn` - identified sequentially
* `whn` - UTC seconds after 1970

You could call this seven-y thing a sentence.
A lex is just a bunch of words.
And each word has these seven attributes.
(All but `txt` are qiki numbers.)


## hello proverbial world

Let's make up some words.
Here is some word-making-upping action
in the Python programming language. 
Before a lex can say hello to the world,
it has to define _world_. And _hello_.
Those are new words.
The lex also has a word for itself.

```
lex = LexInMemory()
hello = lex.verb('hello')
world = lex.noun('world')
```

Once a lex has a verb for hello 
and a noun for world,
then it can say hello to the world.

```
lex[lex](hello)[world] = 42,"How are ya!"
```

The syntax will make a little more sense
if you diagram a sentence with
subjects and objects in squares,
and the verb in a circle.

```
#  _________       __       ________
# |         |    /    \    |        |
# | subject |-->( verb )-->| object |
# |_________|    \ __ /    |________|
```

Okay, it doesn't make a whole lot more sense.
But you see the resemblance right?
Give it time to grow on you.

The hello-world statement is itself a word.
Let's look at this new word.

```
word = lex[lex](hello)[world]

print(int(word.num), word.txt)
# 42 How are ya!

print("{:svo}".format(word))
# Word(sbj=lex,vrb=hello,obj=world)
```


## is a word a sentence?

Yes and no.
Yes every sentence defines a new word.
But no there are some other ways to make up words.

I lied earlier, the subclass `LexSentence` 
contains words of seven attributes each, 
but a `Lex` is simpler.
The only attribute a word really has to have 
is an `idn`.
A word can be anything 
you can identify with a number.
And a lex can be any kind 
of access to identified words.


## is a lex a bunch of sentences?

Almost. 
A lex always provides access 
to a bunch of _words_.
Give a lex an idn and it will give you a word.

```
idn = 7
word = lex[idn]             # These do
word = lex.read_word(idn)   # the same
```

If you know a database with numeric ids
you can make a lex that will provide
a word for any record in that database.
Then you can make up sentences 
that refer to those records.
You could triple-like one record,
suggest corrections to another,
and claim another validates 
some comment somewhere.


## the no-center thing

If you want, 
your lex can connect to other lexes.
Because of dirty tricks with qiki numbers, 
the sentences in your lex
can use the words in any other lex.

If you want help making sense 
of your lex and your words,
the best chance comes from making it all public.
Everyone's job, remember.
You get to rate how well that works.

Human opinions are messy. 
That's what we do.
You may want to use tools to extract meaning
from the mess of human opinions in your lex.
Or you may want to make and share 
tools that do that.


## so what does a word represent?

A word can represent
a skit about cheese,
or that meme your friend would like,
or the cure for your grandmother's cancer,
or the good part of a video,
or whoever designed that curvy part on your phone.

A word can be more 
than a rating.
It can represent any thing,
or relationship between things.
It can be any abstraction at all.
 
A word can represent an algorithm you make
to extract something interesting
from a bunch of other words.
Make up a qiki word for that,
and other lexes can use it.
And rate it.
And reward it.
And encourage more like it.

A word can represent the next big thing
that will make this software obsolete.
Something else is bound to eclipse 
the reckless experiments 
I try to start with qiki,
after they go down in flames
from regulation, 
big ventures, 
bungled financing, 
and patent trolls.
So please steal this idea and redo it right.
Or help me make that more tempting.


## who is this for?

I hope you'll use this package 
to spin up your own lex
and integrate it into your site
and start collecting
opinions and other abstractions.
And share them with other trusted lexes.
A lot of software needs developing too.
This is barely an appetizer of a demo.
Just some quarks 
for the next social physics, 
as it were.

To start, only geeky developer-y types 
will be able to create a lex. 
That should change.


## change

I'm not sure, 
you can decide,
but I think you should be able to change anything
except your history of changes.
I know, right?

This package needs a lot of change
before it can play a part
in the ways mentioned here.
I hope you'll participate.

-- Bob Stein, http://bobste.in/ 

---

http://qiki.info/ 
Generation 2 is running there now. 
Generation 3 is what's in this repo.

It's terrible to start over.
It's worse not to be able to.
Let's start over again.
