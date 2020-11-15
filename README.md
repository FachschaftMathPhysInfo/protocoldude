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
# Configuration

If there is a config.ini file in the folder where the Protocoldude3 is executed, it will be loaded. The config.ini file determines the default settings. It is also possible to specify only a part of the default settings in a config.ini file. Command line arguments overwrite the default settings.

Example of a config.ini file:
```ini
[default]
disable_mail=False
disable_path_check=False
disable_svn=False
disable_tex=False
from_address=simo@mathphys.stura.uni-heidelberg.de
mail_subject_prefix=Gemeinsame Sitzung
```
