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
import sys
import smtplib
import getpass

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
    name = year and month and date and path[4] is '-' and path[7] is '-'

    if not path.endswith('.txt'):
        raise Exception('Der Dateipfad führt nicht zu einem Sitzungsprotokoll oder du schaust besser nochmal über den Filenamen!')
    return True


class Protocol(object):
    """reads in the protocol and processes it"""
    def __init__(self, path):
        # validate filename as protocol (yyyy-mm-dd) and .txt
        self.path = path

        print('\nProtokoll "{}" wird bearbeitet .. \n \n'.format(self.path))

        with open(self.path, 'r') as file:
            self.protocol = file.read().splitlines()
        self.tops = []
        self.mails = False

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
            end = title_lines[i+1] - 1
            top = TOP(i + 1, begin, end)
            self.tops.append(top)

    def rename_title(self):
        """Adjust TOP title type setting"""
        for top in self.tops:
            if not self.protocol[top.start+1].startswith("TOP: "):
                self.protocol[top.start+1] = "TOP " + str(top.number) + ": " + self.protocol[top.start+1]
            else:
                self.protocol[top.start+1] = self.protocol[top.start+1][:3] + str(top.number) + " " + self.protocol[top.start+1][3:]
            length = len(self.protocol[top.start+1])
            self.protocol[top.start+2] = "="*length
            self.protocol[top.start] = "="*length

    def get_users(self):
        for top in self.tops:
            top.get_user(self.protocol)
            top.get_mails()

    def send_mails(self):
        try:
            server = smtplib.SMTP("mail.urz.uni-heidelberg.de", 587)
            login = input('Uni ID für den Mailversand: ')
            server.login(login, getpass.getpass(prompt='Passwort für deinen Uni Account: '))

            for top in self.tops:
                top.send_mail(server, self.protocol)
            server.quit()
            self.mails = True
            print("\nAlle Mails wurden erfolgreich verschickt. \n")
        except Exception as e:
            print(e.what())
            print("\nMails konnten nicht verschickt werden. Hast du die richtigen Anmeldedaten eingegeben?")

    def write_success(self):
        if self.mails:
            now = datetime.datetime.now()
            self.protocol.insert(0, ":Protocoldude: Mails versandt @ {}".format(now.strftime("%H:%M %d.%m.%Y")))
            self.protocol.insert(1, "\n")

        with open(self.path, 'w') as file:
            file.write('\n'.join(self.protocol) + '\n')
        # TODO: more specific exception handling
        try:
            subprocess.run(['svn', 'up'], check=True)
            subprocess.run(['svn', 'add', '{}'.format(self.path)], check=True)
            subprocess.run(['svn', 'commit', '-m', '"Protokoll der gemeinsamen Sitzung hinzugefügt"'], check=True)
            print("Protokoll bearbeitet und in den Sumpf geschrieben.\n Für heute hast du's geschafft!")
        except:
            print("Konnte SVN Update nicht durchführen. \n Das musst Du irgendwie von Hand reparieren mit 'svn cleanup' oder so.")
            print("Das Protokoll wurde trotzdem bearbeitet und gespeichert.")


class TOP(Protocol):
    """
    Separates the several TOPs out of one protocol and provides different 
    functions to further process the sections.
    """

    def __init__(self, number: int, start: int, end: int):
        self.number = number
        self.start = start
        self.end = end
        self.users = []
        self.mails = []

    def get_user(self, protocol: list):
        """searches for all mentioned users in the TOP paragraph"""
        # TODO: recognize multiple users in one line
        for line in protocol[self.start:self.end]:
            # check for mail address
            if "${" in line and "}" in line:
                start = line.index("${")
                end = line.index("}")
                user = line[start+2:end]
                self.users.append(user)

        self.users = list(set(self.users))  # remove duplicates

    def get_mails(self):
        if extract_mails(ldap_search(self.users)) is not None:
            self.mails = extract_mails(ldap_search(self.users))

        for user in self.users:
            if user in LIST_USERS[:][0]:
                self.mails.append(user + "@mathphys.stura.uni-heidelberg.de")

    def send_mail(self, server, protocol):
        for user, mail in zip(self.users, self.mails):
            fromaddr = "fachschaft@mathphys.stura.uni-heidelberg.de"

            msg = MIMEMultipart()
            msg['From'] = fromaddr
            msg['To'] = mail
            msg['Subject'] = "Gemeinsame Sitzung: {}".format(protocol[self.start+1])

            if user in LIST_USERS[:][0]:
                body = LIST_USERS[LIST_USERS[:][0].index(user)][1] + ",\n\n"
            else:
                body = "Hallo {},\n\n".format(user)
            body += "Du sollst über irgendwas informiert werden. Im Sitzungsprotokoll steht dazu folgendes:\n\n{}\n\n\nViele Grüße, Dein SPAM-Skript.".format('\n'.join(protocol[self.start:self.end])+'\n')
            # \n\nSollte der Text abgeschnitten sein, schaue bitte im Sitzungsprotokoll nach (Zeile #{tops[i]} – MathPhys Login notwendig).\n#{url}/#{file}\" | mail -a \"Reply-To: #{$replyto}\" -a \"Content-Type: text/plain; charset=UTF-8\" -s \"#{$subject}: #{title} (#{date})\" '#{mail}';", false) unless $debug

            msg.attach(MIMEText(body, 'plain'))

            text = msg.as_string()
            server.sendmail(fromaddr, mail, text)


def ldap_search(users: list) -> list:
    """ searches for a list of users in our ldap """
    server = ldap.initialize('ldaps://' + MATHPHYS_LDAP_ADDRESS)
    users = ['(uid={})'.format(user) for user in users]
    query = '(|{})'.format("".join(users))
    query_result = server.search_s(
        MATHPHYS_LDAP_BASE_DN,
        ldap.SCOPE_SUBTREE,
        query
    )
    return query_result


def extract_mails(query: list) -> list:
    """ extract mails from nonempty ldap queries """
    mails = []
    if query:
        for result in query:
            # dn = result[0]
            attributes = result[1]
            mails.append(attributes["mail"][0].decode('utf-8'))
    return mails

def main():
    # disables error messages
    sys.tracebacklimit = 0

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "infile",
        metavar="./path/to/file",
        type=argparse.FileType('r'),
        help="Path to the protcol. Expects filename to have have the following format: 'yyyy-mm-dd.txt'"
    )
    parser.add_argument(
        "-v",
        "--version",
        help="Print the version and exit.",
        action="version",
        version=__version__
    )

    args = parser.parse_args()
    check_path(path=args.infile.name)

    protocol = Protocol(path=args.infile.name)
    protocol.get_tops()
    protocol.get_users()
    protocol.rename_title()
    protocol.send_mails()
    protocol.write_success()


if __name__ == "__main__":
    main()
