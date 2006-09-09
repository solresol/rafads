#!/usr/bin/env python

# rafads.py
#  Read A File And Do Something
#
import string
import sys
import os
import glob
import time

# A number of seconds.... (3628800 is 6 weeks)

UNREAD_FILES_RESET_AFTER = 3628800

# ToDo:
#  - alert on missing file (currently just prints to stderr)
#  - implement alternative newline characters
#  - don't have open all pattern-matched files in parallel???
#  - rewrite in C (??)
#  - possibly improve the storing of indexes (doesn't work for
#    filenames with a \n in them)  (actually we can't even name them)
#  - implement index storing (in the registry???) for MS-Windows
#  - implement for other platforms as well.
#  - implement index storing efficiently (!) on Unix

WHERE_TO_STORE_INDEXES = '/tmp/rafads.indexes'
def openIndexFile():
    try:
        return open(WHERE_TO_STORE_INDEXES)
    except IOError:
        # I assume that means it doesn't exist.
        pass
    
    try:
        f = open(WHERE_TO_STORE_INDEXES,'w')
        f.close()
    except IOError:
        # I guess that means I can't create it either.
        # Let's reraise the first problem,  so we can
        # get a sensible error message
        return open(WHERE_TO_STORE_INDEXES)
    
    return open(WHERE_TO_STORE_INDEXES)
    
def getPreviousPositionInFile(filename):
    if filename[-1] != '\n': filename = filename + '\n'
    indexfile = openIndexFile()
    for index in indexfile.readlines():
        breakup = string.split(index,'\t',3)
        if len(breakup) != 3:
            sys.stderr.write('Corruption in ' +WHERE_TO_STORE_INDEXES+
                             ' -- troublesome line is: ' + index)
            continue
        try:
            pos = string.atoi(breakup[0])
            t = string.atof(breakup[1])
        except ValueError:
            sys.stderr.write('Corruption in ' +WHERE_TO_STORE_INDEXES+
                             ' -- troublesome line is: ' + index)
            continue
        fname = breakup[2]
        if fname == filename:
            indexfile.close()
            return (pos,t)
    indexfile.close()
    return (0,time.time())
def setPreviousPositionInFile(filename,position,t=None):
    if filename[-1] != '\n': filename = filename + '\n'
    now = time.time()
    if t is None: t = now
    lines = []
    found_it = 0
    indexfile = openIndexFile()
    for index in indexfile.readlines():
        breakup = string.split(index,'\t',3)
        if len(breakup) != 3:
            sys.stderr.write('Corruption in ' +WHERE_TO_STORE_INDEXES+
                             ' -- troublesome line is: ' + index)
            continue
        try:
            oldpos = string.atoi(breakup[0])
            oldtime = string.atof(breakup[1])
        except ValueError:
            sys.stderr.write('Corruption in ' +WHERE_TO_STORE_INDEXES+
                             ' -- troublesome line is: ' + index)
            continue                
        fname = breakup[2]
        if fname == filename:
            lines.append((position,t,filename))
            found_it = 1
        elif now - oldtime < UNREAD_FILES_RESET_AFTER:
            lines.append((oldpos,oldtime,fname))
    if found_it == 0:
        lines.append((position,t,filename))
    indexfile.close()
    indexfile = open(WHERE_TO_STORE_INDEXES,'w')
    for (pos,tm,fname) in lines:
        indexfile.write(`pos`+'\t'+`tm`+'\t'+fname)
            
        
    

######################################################################
#  Mostly the next portions are to do with reading the configuration
#  rather than the content of the log file.
######################################################################

class notOneOfTheseThanks:
    pass

def readMeAConfigPortion(fd,patterns):
    pos = fd.tell()
    data = fd.readline()
    while (string.strip(data) == '') or (data[0]=='#'):
        data = fd.readline()
        #print " [replaced by ",fd.tell(),"] ",data
        if data == '':
            return (None,"End-of-file")
    print "WORKING (at",pos,") ",data,
    endoflinepos = fd.tell()
    for p in patterns:
        if type(p) == type(""):
            print " --> Does <<",string.strip(data),">> match",p,"?"
            if string.upper(data[:len(p)])==string.upper(p):
                print "       yes, it does match ",p,"!"
                return (p,string.strip(data[len(p):]))
        elif callable(p):
            print " --> Does <<",string.strip(data),">> match",repr(p),"?"
            try:
                fd.seek(pos)
                x = p(fd)
                print "      yes it does match ",repr(p),"!"
                return (p,x)
            except notOneOfTheseThanks:
                fd.seek(endoflinepos)
                continue
    print " Sadly,  no,  <<",string.strip(data),">> does not match any of",repr(patterns)
    fd.seek(pos)
    return (None,None)

class Filter:
    def __init__(self,fd):
        (key,value) = readMeAConfigPortion(fd,["FILTER"])
        if key is None: raise notOneOfTheseThanks()
        self.program = value
        self.output = 'STDOUT'
        self.input = None
        self.only_on_changes = 0
        self.data = {}
        while key is not None:
            (key,value) = readMeAConfigPortion(fd,
                                               ["FILTER-OUTPUT-FILE",
                                                "FILTER-INPUT-FILE",
                                                "RUN-FILTER-ONLY-ON-CHANGES"])
            if key == 'FILTER-OUTPUT-FILE':
                self.output = value
            elif key == 'FILTER-INPUT-FILE':
                self.input = value
            elif key == 'RUN-FILTER-ONLY-ON-CHANGES':
                self.only_on_changes = 1
    def make_stream(self,filename):
        if self.input is None:
            
        

DEFAULT_WHEN_MULTIPLE = "READ-ALL"
VALID_WHEN_MULTIPLE = ["READ-FIRST","READ-LAST","READ-OLDEST","READ-NEWEST",
                   "READ-ALL"]
DEFAULT_ORDERING = "ALPHABETIC"
VALID_ORDERINGS = ["TIME","ALPHABETIC"]

class InvalidOrderByStatement:
    def __init__(self,x): self.x = x

class InvalidWhenMultipleStatement:
    def __init__(self,x): self.x = x
    
class LogFile:
    def __init__(self,fd):
        (f,v) = readMeAConfigPortion(fd,["FILE"])
        if f is None: raise notOneOfTheseThanks()
        self.filename = v
        self.newline = os.linesep
        self.filter = None
        self.conditions = []
        self.ordering = DEFAULT_ORDERING
        self.when_multiple = DEFAULT_WHEN_MULTIPLE
        self.reread = 0
        logfile_statements = ["WHEN-MULTIPLE","ORDER-BY",Filter,
                              "NEWLINE-CHARACTERS",
                              "REREAD-FROM-START",Condition,"END-FILE"]
        key = None
        while key != 'END-FILE':
            (key,value) = readMeAConfigPortion(fd,logfile_statements)
            if key is None:
                raise notOneOfTheseThanks()
            elif key == 'WHEN-MULTIPLE':
                value = string.upper(value)
                if value not in VALID_WHEN_MULTIPLE:
                    raise InvalidWhenMultipleStatement(value)
                self.when_multiple = value
            elif key == 'ORDER-BY':
                value = string.upper(value)
                if value not in VALID_ORDERINGS:
                    raise InvalidOrderByStatement(value)
                self.ordering = value
            elif key is Filter:
                self.filter = value
            elif key == 'REREAD-FROM-START':
                self.reread = 1
            elif key is Condition:
                self.conditions.append(value)
            elif key == 'NEWLINE-CHARACTERS':
                raise 'Alternate new lines are unimplemented'
                self.newline = value
            elif key == 'END-FILE':
                pass
            else:
                raise 'Internal error'
            #self.name_data[key] = value
        
    def getfiles(self):
        final_files = []

        filenames = glob.glob(self.filename)
        if len(filenames) > 1:
            # probably Unix specific....
            def byage(x,y):  return os.stat(x)[8] - os.stat(y)[8]
            if self.when_multiple == 'READ-FIRST':
                filenames.sort()
                filenames = [filenames[0]]
            elif self.when_multiple == 'READ-LAST':
                filenames.sort()
                filenames = [filenames[-1]]
            elif self.when_multiple == 'READ-NEWEST':
                filenames.sort(byage)
                filenames = [filename[0]]
            elif self.when_multiple == 'READ-OLDEST':
                filenames.sort(byage)
                filenames = [filename[-1]]
            elif self.when_multiple == 'READ-ALL':
                if self.ordering == 'ALPHABETIC':
                    filenames.sort()
                elif self.ordering == 'TIME':
                    filenames.sort(byage)
                else:
                    raise 'Unknown ordering',self.ordering

            else:
                raise 'Unknown when-multiple',self.when_multiple

        
        for f in filenames:
            
        
        
        

class EndOfFileReachedWhileReadingEmailBody:
    def __init__(self,x): self.x = x
        

class EmailActivity:
    def __init__(self,fd):
        email_statements = ['EMAIL-BODY-UNTIL',
                            'EMAIL-FROM','EMAIL-SMTP-SERVER']
        self.data = {}
        self.body = ''
        
        (key,value) =  readMeAConfigPortion(fd,['EMAIL-TO'])
        if key is None: raise notOneOfTheseThanks()
        self.address = value

        (key,value) =  readMeAConfigPortion(fd,['EMAIL-SUBJECT'])
        if key is None: raise notOneOfTheseThanks()
        self.subject = value
        
        while key is not None:
            (key,value) = readMeAConfigPortion(fd,email_statements)
            if key == 'EMAIL-BODY-UNTIL':
                ending = value
                line = ''
                while string.strip(line) != ending:
                    self.body = self.body + line
                    line = fd.readline()
                    if line == '':
                        raise EndOfFileReachedWhileReadingEmailBody(key)
            elif key is not None:
                self.data[key] = value


class EndOfFileReachedWhileReadingActionStdin:
    def __init__(self,x): self.x = x
        

class ActionActivity:
    def __init__(self,fd):
        self.stdin_stream = ''
        
        (key,value) = readMeAConfigPortion(fd,['ACTION'])
        if key is None: raise notOneOfTheseThanks()
        self.command = value

        (key,value) = readMeAConfigPortion(fd,['ACTION-STDIN-UNTIL'])
        if key is None:
            self.stdin_stream = None
        else:
            ending = value
            line = ''
            while string.strip(line) != ending:
                self.stdin_stream= self.stdin_stream + line
                line = fd.readline()
                if line == '':
                    raise EndOfFileReachedWhileReadingActionStdin(key)



class Condition:
    def __init__(self,fd):
        condition_lines = ['UNLESS','VARIABLE',EmailActivity,
                           ActionActivity,'SKIP-REMAINING-CONDITIONS',
                           'END-CONDITION','MATCH','VARIABLE']
        self.unless = None
        self.match = None
        self.variables = {}
        self.skip_remaining_conditions = 0
        self.actions = []
        self.emails = []
        (key,value) = readMeAConfigPortion(fd,['CONDITION'])
        if key is None: raise notOneOfTheseThanks()
        self.name = key
        while key != 'END-CONDITION':
            (key,value) = readMeAConfigPortion(fd,condition_lines)
            if key is None: 
                raise notOneOfTheseThanks()
            elif key == 'UNLESS':
                self.unless = value
            elif key == 'MATCH':
                self.match = value
            elif key == 'SKIP-REMAINING-CONDITIONS':
                self.skip_remaining_conditions = 1
            elif key is EmailActivity:
                self.emails.append(value)
            elif key is ActionActivity:
                self.emails.append(value)
            elif key is 'VARIABLE':
                parts = string.split(value,'=>')
                if len(parts)!=2:
                    print "xxxxx --- Sorry, :",parts
                    raise notOneOfTheseThanks()
                try:
                    number = string.atoi(string.strip(parts[0]))
                    name = string.strip(parts[1])
                except ValueError:
                    raise notOneOfTheseThanks()
                self.variables[number] = name
            elif key == 'END-CONDITION':
                pass
            else:
                print "Huh?"
            
                                         
def ReadConfigurationFile(fd):
    if (type(fd)==type('')): fd = open(fd)
    files = []
    k = "not none"
    while k is not None:
        try:
            (k,v) = readMeAConfigPortion(fd,[LogFile])
        except notOneOfTheseThanks:
            print "Syntax error at character ",fd.tell(),"of config file."
            sys.exit()
        if (k is None) and (v == 'End-of-file'):
            pass
        elif k is None:
            print "No match at character ",fd.tell(),"of config file."
        else:
            files.append(v)
    return files

    
