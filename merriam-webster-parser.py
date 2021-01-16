import urllib.request
import json
import os
import re

def parse_resp(resp):
    defs = dict()
    for entry in resp:
        defs.update({parse_date(entry): parse_defs(entry)})

    def_list = []
    for _, value in defs.items():
        #print(value)
        def_list.append(structure_defs(value))
    
    return def_list

def structure_defs(defs):
    if isinstance(defs, dict):
        (key, value) = next(iter(defs.items()))
        return {key: {'def': value}}

    if isinstance(defs, list):
        def_dict = dict()
        curr_num = ''

        def fmt_def(key, value):
            return {key: {'def': value}}

        for d in defs:
            curr_let = ''
            if isinstance(d, list):
                def_dict.update(structure_defs(d))
            if isinstance(d, dict):
                (key, value) = next(iter(d.items()))
                if is_paren(key):
                    def_dict[curr_num][curr_let].update(fmt_def(key, value))
                elif is_number(key):
                    curr_num = key
                    def_dict.update(fmt_def(key, value))
                else:
                    def_dict[curr_num].update(fmt_def(key, value))

        return def_dict
            
def is_number(string):
    try:
        int(string)
        return True
    except:
        return False

def is_paren(string):
    return '(' in string[0]


# First Known Use: date
# Hierarchical Context
#   Top-level member of dictionary entry
# Data Model
#   "date" : string
def parse_date(entry):
    if isinstance(entry, dict):
        if 'date' in entry.keys():
            return entry['date']

    return


# Definition: def
# Hierarchical Context
#   Occurs as top-level member of dictionary entry and in dros.
# Data Model
#   array of one or more objects
def parse_defs(defs):
    if isinstance(defs, dict):
        defs = defs['def']

    for entry in defs:
        if is_vd(entry):
            return parse_vd(entry)

        elif is_sseq(entry):
            return parse_sseq(entry)


# Verb Divider: vd
# Hierarchical Context
#   Occurs in def, preceding an sls (optional) and sseq (required)
# Data Model
#   "vd" : string
def is_vd(vd):
    if isinstance(vd, dict):
        return 'vd' in vd.keys()
    
    return False

def parse_vd(vd):
    return parse_sseq(vd['sseq'])


#
# Shared logic for sseq and pseg
#
def parse_array(array):
    sense_list = []

    for sense in array:
        if is_sense(sense):
            sense_list.append(parse_sense(sense))
        elif is_bs(sense):
            sense_list.append(parse_bs(sense))
        elif is_pseq(sense):
            sense_list.append(parse_pseq(sense))
        elif isinstance(sense, list):
            sense_list.append(parse_array(sense))

    if len(sense_list) == 1:
        return sense_list[0]

    return sense_list


# Sense Sequence: sseq
# Hierarchical Context:
#   Occurs in def
# Data Model:
#   "sseq" : array
def is_sseq(sseq):
    if isinstance(sseq, dict):
        return 'sseq' in sseq.keys()
    
    return False

def parse_sseq(sseq):
    if isinstance(sseq, dict):
        sseq = sseq['sseq']

    sense_list=[]

    for array in sseq:
        sense_list.append(parse_array(array))

    if len(sense_list) == 1:
        return sense_list[0]

    return sense_list


# Parenthesised Sense Sequence:
# Hierarchical Context:
#   Occurs as an element in an sseq array.
# Data Model:
#   array consisting of one or more sense elements and an optional bs element.
def is_pseq(pseq):
    if isinstance(pseq, list):
        return pseq[0] == 'pseq'
    
    return False


def parse_pseq(pseq):
    sense_list = []

    for sense in pseq[1:]:
        sense_list.append(parse_array(sense))

    return sense_list


# Binding Substitution: bs
# Hierarchical Context
#   Occurs as an element in an sseq or pseq array, where it is followed by one or more sense elements.
# Data Model:
#   array of the form ["bs", {sense}]
def is_bs(bs):
    if isinstance(bs, list):
        return 'bs' == bs[0]
    
    return False


def parse_bs(bs):
    return parse_sense(bs[1])


# Sense: sense
# Hierarchical Context
#   Occurs as an element in an sseq array.
# Data Model:
#    object or array consisting of one dt (required) and zero or more et, ins, lbs, prs, sdsense, sgram, sls, sn, or vrs
def is_sense(sense):
    if isinstance(sense, dict):
        return 'sense' in sense.keys()
    elif isinstance(sense, list):
        return 'sense' == sense[0]
    
    return False


def parse_sense(sense):
    if isinstance(sense, dict):
        sense = sense['sense']
    elif isinstance(sense, list):
        sense = sense[1]
    else: return

    sn = 1
    if 'sn' in sense.keys():
        sn = sense['sn']

    dt = parse_dt(sense['dt'])
    if 'sdsense' in sense.keys():
        dt += parse_sdsense(sense['sdsense'])

    return {sn: dt}


# Divided Sense: sd
# Hierarchical Context
#   Occurs within a sense, where it is always preceded by dt.
# Data Model:
#   "sdsense" : object with the following members:
#   "sd" : string	sense divider (required)
#   et, ins, lbs, prs, sgram, sls, vrs	(optional)
#   dt	definition text (required)
def parse_sdsense(sdsense):
    return parse_dt(sdsense['dt'])


# Defining Text: dt
#Hierarchical Context
#   Occurs as an element in an sseq array.
# Data Model:
#   "dt" : array consisting of one or more elements:
#   ["text", string] where string contains the definition content (required)
#   optional bnw, ca, ri, snote, uns, or vis elements
def parse_dt(dt):
    for elem in dt:
        if elem[0] == 'text':
            ### Implement text cleaning
            return re.sub(r'\{[\w]*\}', '', elem[1])