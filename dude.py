#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# possible input mail adresses:
#     ${internal}          => internal@mathphys.stura.uni-heidelberg.de
#     ${external@some.com} => external@some.com

import argparse
import datetime
import subprocess
import re
import smtplib
import getpass
import tempfile
import urllib.request
import sys
import os

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import ldap

__version__ = "v3.0.2"

MATHPHYS_LDAP_ADDRESS = "ldap1.mathphys.stura.uni-heidelberg.de"
MATHPHYS_LDAP_BASE_DN = "ou=People,dc=mathphys,dc=stura,dc=uni-heidelberg,dc=de"

# define common mail lists and aliases
LIST_USERS = [
    ["fachschaft", "Liebe Fachschaft"],
    ["flachschaft", "Liebe Fachschaft"],
    ["bernd", "Liebe Fachschaft"],
    ["fsinformatik", "Liebe Fachschaft"],
    ["fsphysik", "Liebe Fachschaft"],
    ["fsmathematik", "Liebe Fachschaft"],
    ["fsmathinf", "Liebe Fachschaft"],
    ["infostudkom", "Liebes Mitglied der Studienkommission Informatik"],
    ["tistudkom", "Liebes Mitglied der Studkom TI"],
    ["mathstudkom", "Liebe MathStudKomLerInnen"],
    ["mathestudkom", "Liebe MathStudKomLerInnen"],
    ["physstudkom", "Liebe Mitglied der Studkom Physik"],
    ["physikstudkom", "Liebe Mitglied der Studkom Physik"],
    ["studkomphysik", "Liebe Mitglied der Studkom Physik"],
    ["scstudkom", "Liebe Mitglied der Studkom SciCom"],
    ["mathfakrat", "Liebes Mitglied des MatheInfo-Fakrats"],
    ["fakratmathinf", "Liebes Mitglied des MatheInfo-Fakrats"],
    ["physfakrat", "Liebes Mitglied des Physik-Fakrats"],
    ["fakratphys", "Liebes Mitglied des Physik-Fakrats"],
    ["fakratphysik", "Liebes Mitglied des Physik-Fakrats"],
    ["akfest", "Liebes Mitglied der AK-Fest Liste"],
    ["vertagt", "Liebe SiMo"],
    ["schluesselinhaber", "Liebe/r Bewohner/in des Fachschaftsraums"],
    ["finanzen", "Sehr geehrte Menschen mit Ahnung der vielen Goldbarren"]
]

class Protocol(object):
    """reads in the protocol and processes it"""

    def __init__(self, args):
        # validate filename as protocol (yyyy-mm-dd) and .txt
        self.args = args
        self.path = args.infile

        print('\nProtokoll "{}" wird bearbeitet ..\n'.format(self.path))

        if "http" in self.path:
            self.protocol = self.download_protocol(self.path)
            splitted = self.path.split("/")
            self.path = splitted[len(splitted)-1]+'.txt'
        else:
            with open(self.path, "r") as file:
                self.protocol = file.read().splitlines()
        self.tops = []
        self.mails_sent = False
        self.unknown = []

    def check_path(self) -> bool:
        """
        Checks the input file name for a valid date and type .txt
        """
        # year = path[0:4].isnumeric()
        # month = path[5:7].isnumeric()
        # date = path[8:9].isnumeric()
        # name = year and month and date and path[4] is "-" and path[7] is "-"
        #
        # if not path.endswith(".txt"):
        #     raise Exception(
        #         "Der Dateipfad führt nicht zu einem Sitzungsprotokoll oder du schaust besser nochmal über den Filenamen!"
        #     )
        # return True

        filename_match = re.match("^20\d{2}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01]).txt{1}$", self.path)

        if not os.path.isfile(self.path):
            raise FileNotFoundError("Der Dateipfad führt nicht zu einem Sitzungsprotokoll!")

        while not filename_match:
            print("Den Dateipfad {} solltest du in das Datum der Sitzung ändern! Das sollte dann so aussehen: yyyy-mm-dd.txt".format(self.path))
            new_path = input("Bitte gib den korrekten Dateinamen an: ")

            filename_match = re.match("^20\d{2}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01]).txt{1}$", new_path)
            os.rename(self.path, new_path)
            self.path = new_path
        return True


    def download_protocol(self, url, save_path=""):
        """
        Downloads a protocol
        URL: The URL to download the Protocol from
        """
        export_suffix = ""
        if "pad" in url:
            export_suffix = "/export/txt"
        # if "notes" in url:
            # import kerberos
            # __, krb_context = kerberos.authGSSClientInit("chris")
            # kerberos.authGSSClientStep(krb_context, getpass.getpass(prompt="Passwort für deinen Account: "))
            # kerberos.authGSSClientStep(krb_context, "")
            # negotiate_details = kerberos.authGSSClientResponse(krb_context)
            # headers = {"Authorization": "Negotiate " + negotiate_details}
            # print(headers)
        if not save_path:
            save_path = tempfile.NamedTemporaryFile()
            urllib.request.urlretrieve(url+export_suffix, save_path.name)
            with save_path.file as f:
                protocol = [line.decode("utf-8") for line in f.read().splitlines()]
            print(save_path.name)
            return protocol
        else:
            urllib.request.urlretrieve(url, save_path)

    def get_tops(self):
        """separate the given protocol in several TOPs from '===' to '==='"""
        title_lines = []

        for i in range(len(self.protocol) - 2):
            line_a = self.protocol[i]
            line_b = self.protocol[i + 2]

            if line_a.startswith("===") and line_b.startswith("==="):
                title_lines.append(i)

        title_lines.append(len(self.protocol) + 1)

        for i in range(len(title_lines) - 1):
            begin = title_lines[i]
            end = title_lines[i+1] - 1
            top = TOP(i + 1, begin, end, self.protocol, self.args)
            self.tops.append(top)

    def rename_title(self):
        """Adjust TOP title type setting"""
        for top in self.tops:
            top.rename()

    def get_users(self):
        for top in self.tops:
            top.get_user()
            self.unknown = top.get_mails()

    def send_mails(self, username="", tries=0):
        try:
            server = smtplib.SMTP("mail.urz.uni-heidelberg.de", 587)
            prompt = "Passwort für deinen Uni Account: "
            if not username:
                username = input("Uni ID für den Mailversand: ")
            prompt = "Passwort für {}: ".format(username)
            server.login(
                username, getpass.getpass(prompt=prompt)
            )

            mailcount = 0
            for top in self.tops:
                mailcount += top.send_mail(server)
            server.quit()
            self.mails_sent = True
            if mailcount == 1:
                print("\nEs wurde erfolgreich eine Mail versendet!\n")
            else:
                print("\nEs wurden erfolgreich {} Mails verschickt.\n".format(mailcount))
            if self.unknown:
                print("An folgende Nutzer konnte aus unerklärlichen Gründen keine Mail versandt werden:")
                for user in self.unknown:
                    print("    - {}".format(user))
        except smtplib.SMTPAuthenticationError:
            print("Du hast die falschen Anmeldedaten eingegeben!")
            print("Bitte versuche es noch einmal:")
            self.send_mails(username=username, tries=tries+1)
        except Exception as e:
            print(e)
            print(
                "\nMails konnten nicht verschickt werden. Hast du die richtigen Anmeldedaten eingegeben?"
            )

    def write_success(self):
        if self.mails_sent:
            now = datetime.datetime.now()
            self.protocol.insert(
                0,
                ":Protocoldude: Mails versandt @ {}".format(
                    now.strftime("%H:%M %d.%m.%Y")
                ),
            )
            self.protocol.insert(1, "\n")

        with open(self.path, "w") as file:
            file.write("\n".join(self.protocol) + "\n")

    def svn_interaction(self):
        # TODO: more specific exception handling
        try:
            subprocess.run(["svn", "up"], check=True)
            subprocess.run(["svn", "add", "{}".format(self.path)], check=True)
            subprocess.run(
                [
                    "svn",
                    "commit",
                    "-m",
                    '"Protokoll der gemeinsamen Sitzung hinzugefügt"',
                ],
                check=True,
            )
            print(
                "Protokoll bearbeitet und in den Sumpf geschrieben.\n Für heute hast du's geschafft!"
            )
        except:
            print(
                "Konnte SVN Update nicht durchführen. \n Das musst Du irgendwie von Hand reparieren mit 'svn cleanup' oder so."
            )
            print("Das Protokoll wurde trotzdem bearbeitet und gespeichert.")

class TOP(Protocol):
    """
    Separates the several TOPs out of one protocol and provides different
    functions to further process the sections.
    """

    def __init__(self, number: int, start: int, end: int, protocol, args):
        self.args = args
        self.number = number
        self.start = start
        self.end = end
        self.users = []
        self.unknown = []
        self.mails = []
        self.protocol = protocol
        self.title = TOP_Title(start, start+3, self.protocol[start+1])
        self.send = 0

    def __str__(self):
        return "\n".join(self.protocol[self.start:self.end])

    def rename(self):
        self.title.rename(self.number)
        # apply the changes in the title to the protocol
        title = self.title.list()
        for p_index, t_index in zip(range(self.title.start, self.title.end), range(len(title))):
            self.protocol[p_index] = title[t_index]

    def get_user(self):
        """searches for all mentioned users in the TOP paragraph"""
        users = []
        for line in self.protocol[self.start:self.end]:
            # check for mail address
            adress = re.findall(r"\$\{(.*?)\}", line)
            users += adress
        self.users = list(set(users))  # remove duplicates


    def get_mails(self):
        mailinglistusers = []
        for user in self.users:
            # if user in List_user append valid mail to "mails" else add user to not found
            if any(user.lower() in account for account, greeting in LIST_USERS):
                self.mails.append(user + "@mathphys.stura.uni-heidelberg.de")
            else:
                result = extract_mails(ldap_search(self.users, self.unknown)) # search remaining users in LDAP
                print("Result: {}".format(result))
                if self.mails:
                    if result:
                        self.mails += result
                    else:
                        self.unknown.append(result)
                else:
                    self.mails = result

        return self.unknown

    def send_mail(self, server) -> int:

        print(self.title)
        print(self.users)
        print(self.mails)
        for user, mail in zip(self.users, self.mails):
            from_addr = self.args.from_address

            msg = MIMEMultipart()
            msg["From"] = from_addr
            msg["To"] = mail
            msg["Subject"] = self.args.mail_subject_prefix + ": " + self.title.title_text

            if any(user.lower() in account for account, greeting in LIST_USERS):
                body = [greeting for [account, greeting] in LIST_USERS if account == user.lower()][0] + ",\n\n"
            else:
                body = "Hallo {},\n\n".format(user)
            body += "Du sollst über irgendwas informiert werden. Im Sitzungsprotokoll steht dazu folgendes:\n\n{}\n\n\nViele Grüße, Dein SPAM-Skript.".format(self.__str__())
            # \n\nSollte der Text abgeschnitten sein, schaue bitte im Sitzungsprotokoll nach (Zeile #{tops[i]} – MathPhys Login notwendig).\n#{url}/#{file}\" | mail -a \"Reply-To: #{$replyto}\" -a \"Content-Type: text/plain; charset=UTF-8\" -s \"#{$subject}: #{title} (#{date})\" '#{mail}';", false) unless $debug

            msg.attach(MIMEText(body, "plain"))
            text = msg.as_string()
#            server.sendmail(from_addr, mail, text)
            self.send +=1
            self.users.remove(user)
            self.mails.remove(mail)
            print(user)
            print('Mail an "{}" zu {} gesendet.'.format(user, self.title.title_text))
        return self.send


def ldap_search(users: list, unknown: list) -> list:
    """ searches for a list of users in our ldap """
    server = ldap.initialize("ldaps://" + MATHPHYS_LDAP_ADDRESS)
    users_old = users
    users = [(user, "(uid={})".format(user)) for user in users]
    users = [(
        user, server.search_s(
            MATHPHYS_LDAP_BASE_DN,
            ldap.SCOPE_SUBTREE,
            query
        )
    ) for user, query in users]

    # Remove all users without query results
    users = [user for user in users if user[1]]
    if len(users) < len(users_old):
        non_found = [
            old_user for old_user in users_old if old_user not in
            [user[0] for user in users]
        ]
        if len(non_found) >= 1:
            print(f"The following user could not be found in the LDAP: \"{non_found[0]}\"")
            raise RuntimeError(
               f"The following user could not be found in the LDAP: \"{non_found[0]}\""
            )
        userstring = "\"" + "\", \"".join(non_found) + "\""
        raise RuntimeError(
            f"The following user could not be found in the LDAP: {userstring}"
        )
    print("LDAP: ")
    print(users)
    return users

def extract_mails(query: list) -> list:
    """ extract mails from nonempty ldap queries """
    mails = []
    if query:
        for user, result in query:
            # dn = result[0]
            if result:
                attributes = result[0][1]
                mails.append(attributes["mail"][0].decode("utf-8"))
            # TODO: Implement select of alternatives
    return mails


class TOP_Title:
    def __init__(self):
        self.start = -1
        self.end = -1
        self.title_text = ""

    def __init__(self, start, end, title_text):
        self.start = start
        self.end = end
        self.title_text = title_text

    def __str__(self):
        return_str = ""
        if self.title_text:
            length = len(self.title_text)
            return_str = "=" * length
            return_str += "\n" + self.title_text + "\n"
            return_str += "=" * length
        return return_str

    def list(self):
        return str(self).split("\n")

    def rename(self, number):
        if not re.search(r'(?i)TOP\s+\d+:', self.title_text):
            self.title_text = "TOP {}: {}".format(number, self.title_text)

def main():
    # comment to disables error messages
    # sys.tracebacklimit = 0

    parser = argparse.ArgumentParser(description='''
        Der Protocoldude macht automagisch aus deinem schnell zusammen geschriebenen inoffiziellen Protokoll eine ansehnliche Version.
        Außerdem werden auf seltsame Weise Erinnerungs-Maills versandt.
        Gib dazu folgenden Befehl im Zielordner mit vorhandenem Protokoll ein:
            $ python3 protocoldude.py yyyy-mm-dd.txt
        Damit der ganze Spaß funktioniert, solltest du aber trotzdem ein paar Formalia beachten. Dazu gehören:
        - Überschriften erfüllen die Form:
                ===
                TOP: <name>
                ===
        - Zu benachrichtigende Personen werden erwähnt:
                ${<intern>}
                ${<external@some.com>}
        ''',
        epilog="Wer schlau ist, liest zwischen den Zeilen (oder im Code).")
    parser.add_argument(
        "infile",
        metavar="<file>",
        help="Pfad zum Protokoll. Die angegebene Datei muss folgende Benennung haben: 'yyyy-mm-dd.txt'",
    )
    parser.add_argument(
        "--disable-svn",
        help="Schaltet die SVN Interaktion ab.",
        action="store_true",
        dest="disable_svn",
    )
    parser.add_argument(
        "--disable-path-checking",
        help="Verhindert eine Überprüfung des angegebenen Dateinamens.",
        action="store_true",
        dest="disable_path_check",
    )
    parser.add_argument(
        "--disable-mail",
        help="Unterdrückt das Senden von Mails.",
        action="store_true",
        dest="disable_mail",
    )
    parser.add_argument(
        "--fromaddr",
        help="Setze den Absender für die zu erstellenden Mails.",
        action="store",
        default="simo@mathphys.stura.uni-heidelberg.de",
        dest="from_address",
    )
    parser.add_argument(
        "--mail-subject",
        help="Ändere den Betreff für die zu erstellenden Mails.",
        action="store",
        default="Gemeinsame Sitzung",
        dest="mail_subject_prefix",
    )
    parser.add_argument(
        "-v",
        "--version",
        help="Gib die Version an ohne das Programm auszuführen.",
        action="version",
        version=__version__,
    )

    if len(sys.argv)==1: # print help message if no arguments were given
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()

    protocol = Protocol(args)
    if not args.disable_path_check:
        protocol.check_path()
    protocol.get_tops()
    protocol.get_users()
    protocol.rename_title()
    if not args.disable_mail:
        protocol.send_mails()
    else:
        print("Mailversand nicht aktiviert!")
    protocol.write_success()
    if not args.disable_svn:
        protocol.svn_interaction()
    else:
        print("Nichts ins SVN commited!")

if __name__ == "__main__":
        main()
