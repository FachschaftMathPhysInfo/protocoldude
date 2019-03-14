#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# possible input mail adresses:
#     ${internal}          => internal@mathphys.stura.uni-heidelberg.de
#     ${external@some.com} => external@some.com
#     ${external@some.com Some Name} => external@some.com
#     ${Some Name external@some.com} => external@some.com

import argparse
import datetime
import subprocess
import re
import smtplib
import getpass
import tempfile
import urllib.request

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import ldap

__version__ = "v1.0.0"

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
]


def check_path(path: str) -> bool:
    """checks the input file name for a valid date and type .txt"""
    year = path[0:4].isnumeric()
    month = path[5:7].isnumeric()
    date = path[8:9].isnumeric()
    name = year and month and date and path[4] is "-" and path[7] is "-"

    if not path.endswith(".txt"):
        raise Exception(
            "Der Dateipfad führt nicht zu einem Sitzungsprotokoll oder du schaust besser nochmal über den Filenamen!"
        )
    return True


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
        check_path(path=self.path)

    def download_protocol(self, url, save_path=""):
        """Downloads a protocol

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
                title_lines.append(i + 1)

        title_lines.append(len(self.protocol) + 1)

        for i in range(len(title_lines) - 1):
            begin = title_lines[i] + 2
            end = title_lines[i + 1] - 1
            top = TOP(i + 1, begin, end, self.args)
            self.tops.append(top)

    def rename_title(self):
        """Adjust TOP title type setting"""
        for top in self.tops:
            if not self.protocol[top.start + 1].startswith("TOP"):
                self.protocol[top.start + 1] = (
                    "TOP " + str(top.number) + ": " + self.protocol[top.start + 1]
                )
            else:
                self.protocol[top.start + 1] = (
                    self.protocol[top.start + 1][:3]
                    + str(top.number)
                    + " "
                    + self.protocol[top.start + 1][3:]
                )
            length = len(self.protocol[top.start + 1])
            self.protocol[top.start + 2] = "=" * length
            self.protocol[top.start] = "=" * length

    def get_users(self):
        for top in self.tops:
            top.get_user(self.protocol)
            top.get_mails()

    def send_mails(self):
        try:
            server = smtplib.SMTP("mail.urz.uni-heidelberg.de", 587)
            login = input("Uni ID für den Mailversand: ")
            server.login(
                login, getpass.getpass(prompt="Passwort für deinen Uni Account: ")
            )

            for top in self.tops:
                top.send_mail(server, self.protocol)
            server.quit()
            self.mails_sent = True
            print("\nAlle Mails wurden erfolgreich verschickt. \n")
        except Exception as e:
            print(e.what())
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

    def __init__(self, number: int, start: int, end: int, args):
        self.args = args
        self.number = number
        self.start = start
        self.end = end
        self.users = []
        self.mails = []

    def get_user(self, protocol: list):
        """searches for all mentioned users in the TOP paragraph"""
        users = []
        for line in protocol[self.start : self.end]:
            # check for mail address
            adress = re.findall("\$\{(.*?)\}", line)
            users += adress
        self.users = list(set(users))  # remove duplicates

    def get_mails(self):
        if extract_mails(ldap_search(self.users)) is not None:
            self.mails = extract_mails(ldap_search(self.users))

        for user in self.users:
            if user in LIST_USERS[:][0]:
                self.mails.append(user + "@mathphys.stura.uni-heidelberg.de")

    def send_mail(self, server, protocol):
        for user, mail in zip(self.users, self.mails):
            from_addr = self.args.from_address

            msg = MIMEMultipart()
            msg["From"] = from_addr
            msg["To"] = mail
            msg["Subject"] = self.args.mail_subject_prefix+":"+protocol[self.start + 1]

            if user in LIST_USERS[:][0]:
                body = LIST_USERS[LIST_USERS[:][0].index(user)][1] + ",\n\n"
            else:
                body = "Hallo {},\n\n".format(user)
            body += "Du sollst über irgendwas informiert werden. Im Sitzungsprotokoll steht dazu folgendes:\n\n{}\n\n\nViele Grüße, Dein SPAM-Skript.".format(
                "\n".join(protocol[self.start : self.end]) + "\n"
            )
            # \n\nSollte der Text abgeschnitten sein, schaue bitte im Sitzungsprotokoll nach (Zeile #{tops[i]} – MathPhys Login notwendig).\n#{url}/#{file}\" | mail -a \"Reply-To: #{$replyto}\" -a \"Content-Type: text/plain; charset=UTF-8\" -s \"#{$subject}: #{title} (#{date})\" '#{mail}';", false) unless $debug

            msg.attach(MIMEText(body, "plain"))

            text = msg.as_string()
            server.sendmail(from_addr, mail, text)


def ldap_search(users: list) -> list:
    """ searches for a list of users in our ldap """
    server = ldap.initialize("ldaps://" + MATHPHYS_LDAP_ADDRESS)
    users = ["(uid={})".format(user) for user in users]
    query = "(|{})".format("".join(users))
    query_result = server.search_s(MATHPHYS_LDAP_BASE_DN, ldap.SCOPE_SUBTREE, query)
    return query_result


def extract_mails(query: list) -> list:
    """ extract mails from nonempty ldap queries """
    mails = []
    if query:
        for result in query:
            # dn = result[0]
            attributes = result[1]
            mails.append(attributes["mail"][0].decode("utf-8"))
    return mails


def main():
    # disables error messages
    # sys.tracebacklimit = 0

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "infile",
        metavar="<file>",
        help="Path to the protcol. Expects filename to have have the following format: 'yyyy-mm-dd.txt'",
    )
    parser.add_argument(
        "--disable-svn",
        help="disable the svn interaction",
        action="store_true",
        dest="disable_svn",
    )
    parser.add_argument(
        "--disable-mail",
        help="disable the sending of mails",
        action="store_true",
        dest="disable_mail",
    )
    parser.add_argument(
        "--fromaddr",
        help="Set 'From:' address for the generated mail",
        action="store",
        default="fachschaft@mathphys.stura.uni-heidelberg.de",
        dest="from_address",
    )
    parser.add_argument(
        "--mail-subject",
        help="Set the subject for the generated mail",
        action="store",
        default="Gemeinsame Sitzung",
        dest="mail_subject_prefix",
    )
    parser.add_argument(
        "-v",
        "--version",
        help="Print the version and exit.",
        action="version",
        version=__version__,
    )

    args = parser.parse_args()

    protocol = Protocol(args)
    protocol.get_tops()
    protocol.get_users()
    # protocol.rename_title()
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
