# qiki - rate anything

A qiki is a no-center public record 
of what anybody thinks of anything.
Including what we think of each others' thinking.
And what we think of each other.
Crazy, right?


## get good

The best opportunity for human betterment today
is to get good at deciding:

1. what **is**
2. what **ought** to be
3. what to **do**

Let's get much better at these now.

Great consequences will not happen until we do.
We don't want to agree. 
But we must decide.

We must find a way to decide 
what is happening.
We need some agreement on what is happening
before we can talk about what matters.
We need some agreement on what matters
before we can talk about what to do.

Who is we?
This applies to every group you can think of.
I think the opportunity is overripe
for getting better at group decisions.


## how

I think the gizmos can help.
Start by storing our thinking out of the silos.
Then anybody can start looking for patterns.
And turning the gizmos loose looking for patterns.
And looking for meaning.

The time to create value and safety
by obscuring will soon be over.
It's time to put all our thinking on the table.

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
no subset is smart enough,
to decide the most important decisions.
Or decide who decides them.
This has to be everyone's job.
Yes its going to be very hard. 
Let's get started.


## word

A qiki **word**, like a natural language word, 
can represent anything.
Unlike a natural language word 
you can make up a lot of them easily.

When you make up a new qiki word 
you string together three other qiki words:

* subject
* verb
* object

and you give the new word its own special:

* number 
(1 means normal, 
2 means you mean it twice as much.
Numbers are awesome.
They can be tiny, they can be huge.
And you get to say what they mean.)
* text 
(because you've got a lot of splainin to do)

and store this stuff in a lex. 


## lex

A lex is a dictionary for your made-up words.
For each word a lex will remember:

* id number
* when you defined it

So that's 7 parts to a word. 
Here's what they're called:

* `sbj` - subject 
* `vrb` - verb
* `obj` - object
* `num` - quantify
* `txt` - name, explain, discuss
* `idn` - identified by a number
* `whn` - seconds after 1970 (or before)

You could call this seven-y thing a sentence.
A lex is just a bunch of words.
And each word has these seven attributes.


## hello proverbial world

Here is some word make-upping action. 
Before a lex can say hello to the world,
it has to define _world_. And _hello_.
Those are new words to be made up.
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
lex[lex](hello)[world] = 1,"First comment!"
```

This syntax will make a little more sense
if you diagram a sentence as
subjects and objects with squares,
and the verb in a circle.

```
#  _________       __       ________
# |         |    /    \    |        |
# | subject |-->( verb )-->| object |
# |_________|    \ __ /    |________|
```

Okay, it doesn't make any more sense.
But you see the resemblance right?
Give it time to grown on you.

The hello-world statement is itself a word.
Let's look at this new word.

```
word = lex[lex](hello)[world]

print(word.txt)
# First comment!

print("{:svo}".format(word))
# Word(sbj=lex,vrb=hello,obj=world)
```


## so a word is a sentence?

Yes and no.
Yes every sentence defines a new word.
But no there are other ways to make up words.

I lied earlier,
the only attribute a word really has to have 
is an `idn`.
A word can be anything 
you can identify with a number.
And a lex can be any collection 
of uniquely identified words.


## is a lex just a bunch of sentences?

Almost. 
A lex is always a bunch of words.
Give a lex an idn and it'll give you a word.

```
word = lex[idn]             # These do
word = lex.read_word(idn)   # the same thing
```

If you have a database with numeric ids
you can make a lex that will churn out
a word for any record in that database.
Then a lex of sentences can refer to 
those words.


## so what is a word??

Yeah, a word can be a lot more than just a rating.
It can represent a thing,
or a relationship between things.
It can be any abstraction at all.


## the no-center thing

Now if you want, 
your lex can connect to other lexes.
Because of dirty tricks with qiki numbers, 
your sentences can use the words in any other lex.

If you want help making sense 
of your lex and your words
the best part happens when you make it all public.
Everyone's job, remember.
You get to rate how we all do.

Human opinions are messy. 
That's what we do.
You may want tools to extract meaning
from the mess of human opinion on your lex.
Or you may want to make and share tools.

To start, only geeky developer-y types 
will be able to create a lex. 
That should change.


## change

Not sure, 
you can decide,
but I think you should be able to change anything
but your history of changes.
I know, right.
