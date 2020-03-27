# Requirements
In order to run `protocoldude3.py` you need to install a few python modules.

The needed modules are listen in the file `requirements.txt`, you can therefore install them using `pip`.
```
# pip3 install -r requirements.txt
```

or

```
$ pip3 install --user -r requirements.txt
```

# Running the program

```bash
$ ./protocoldude3.py <filename>
```
The name of the protocol is expected to have the format `yyyy-mm-dd.txt`.
You can get more informations by invoking the program with the `-h` flag or without any arguments.

## parsed sequences

### agenda items

It is possible to seperate agenda items like this:

```
===
TOP 1: Usage of the protocoldude
===

or

===
Introduction
===
```

They will then be prepended with the sufficent amount of '`=`' to look like this:

```
=================================
TOP 1: Usage of the protocoldude
=================================

===================
TOP 2: Introduction
===================
```

### usernames

Usernames are recogized when annotated like this and are then sent the full agenda item:

```
[...] ${kai-uwe} [...]                      => Dear kai-uwe: kai-uwe@some.com
[...] ${external@some.com} [...]            => Dear external: external@some.com
[...] ${external@some.com Some Name} [...]  => Dear Some Name: external@some.com
[...] ${Some Name external@some.com} [...]  => Dear Some Name: external@some.com
```
