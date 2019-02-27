# Requirements
In order to run `dude.py` you need to install a few python modules.
The needed modules are listen in the file `requirements.txt`, you can therefore install them using `pip`.
```bash
# pip3 install -r requirements.txt
```

or

```bash
$ pip3 install --user -r requirements.txt
```

# Running the program

```bash
$ ./dude.py _protcol.txt_
```
The name of the protocol should be in the format `yyyy-mm-dd.txt`.

## parsed sequences

### agenda items

It is possible to seperate agenda items like this:

```
===
Item 1: Usage of the protocoldude
===
```

They will then be prepended with the sufficent amout of '=' to look like this:

```
=================================
Item 1: Usage of the protocoldude
=================================
```

### usernames

Usernames are recogized when annotated like this and are then sent the full agenda item:

```
[...] ${kai-uwe} [...]
```
