import bs4
import sys
import xmltodict
import collections

duration_to_note_attrs = { # we only support up to 32nd notes
    #32nds
    32: {'type': '32nd'},

    # 16th triplets
    42: {
        'type': '16th',
        'time-modification': {
            'actual-notes': 3,
            'normal-notes': 2,
            'normal-type': '16th'
        }
    },
    43: {
        'type': '16th',
        'time-modification': {
            'actual-notes': 3,
            'normal-notes': 2,
            'normal-type': '16th'
        }
    },

    # 16ths
    63: {'type': '16th'},
    64: {'type': '16th'},

    # dotted 16ths
    96: {'type': '16th', 'dot': ''},

    # 8th triplets
    84: {
        'type': 'eighth',
        'time-modification': {
            'actual-notes': 3,
            'normal-notes': 2,
            'normal-type': 'eighth'
        }
    },
    85: {
        'type': 'eighth',
        'time-modification': {
            'actual-notes': 3,
            'normal-notes': 2,
            'normal-type': 'eighth'
        }
    },
    86: {
        'type': 'eighth',
        'time-modification': {
            'actual-notes': 3,
            'normal-notes': 2,
            'normal-type': 'eighth'
        }
    },

    # 8ths
    127: {'type': 'eighth'}, # for rounding when tripletizing up
    128: {'type': 'eighth'},
    129: {'type': 'eighth'}, # for rounding when tripletizing up

    # dotted 8ths
    192: {'type': 'eighth', 'dot': ''},

    # quarter triplets
    170: {
        'type': 'quarter',
        'time-modification': {
            'actual-notes': 3,
            'normal-notes': 2,
            'normal-type': 'quarter'
        }
    },
    171: {
        'type': 'quarter',
        'time-modification': {
            'actual-notes': 3,
            'normal-notes': 2,
            'normal-type': 'quarter'
        }
    },
    172: {
        'type': 'quarter',
        'time-modification': {
            'actual-notes': 3,
            'normal-notes': 2,
            'normal-type': 'quarter'
        }
    },

    # quarter
    256: {'type': 'quarter'},

    # dotted quarter
    384: {'type': 'quarter', 'dot': ''},

    # half
    512: {'type': 'half'},

    # dotted half
    768: {'type': 'half', 'dot': ''},

    # whole
    1024: {'type': 'whole'}
}

def parse_note(note, prevNoteDur):
    if type(note) is dict or type(note) is collections.OrderedDict: # otherwise it's a rest and we ignore it

        # if 'rest' in note:
        #     return note
            
        duration = int(note['duration'])
        diff = prevNoteDur - duration
        print '{} - {} = {}'.format(prevNoteDur, duration, diff)

        if diff > 0:
            print 'note of duration {} is now a rest'.format(duration)
            return 'rest'

        # testing
        if 'dot' not in note:
            if 'time-modification' in note:
                duration = duration * 1.5 # todo: smartly tripletize
            else:
                duration = duration * 2

        duration = int(duration)
        note_attrs = duration_to_note_attrs[duration]

        note['duration'] = str(duration)
        note['type'] = note_attrs['type']
        if 'dot' in note_attrs:
            note['dot'] = note_attrs['dot']
        else:
            note.pop('dot', None)
        if 'time-modification' in note_attrs['type']:
            note['time-modification'] = note_attrs['time-modification']
        else:
            note.pop('time-modification', None)

        note.pop('default-x', None)

        print '{}, {}'.format(note['duration'], note_attrs)
    return note

def tripletize_duration(duration):
    return duration*2/3

def make_data_document(data, label):
    return {'data': {
        label: data
    }}

def debug_unparse(data, label):
    return xmltodict.unparse(make_data_document(data, label))

# def remove_rests(note):
    # return

if __name__ == '__main__':
    score_xml_in_path = sys.argv[1]
    score_xml_out_path = sys.argv[2]

    score_xml = ''

    with open(score_xml_in_path, 'r') as f:
        score_xml = f.read()

    score_json = xmltodict.parse(score_xml)
    measures = score_json['score-partwise']['part']['measure'] # a list
    
    for mi, measure in enumerate(measures):
        notes = measure['note']
        prevNoteDur = 0
        print 'num notes before: {}'.format(len(notes))

        for ni, note in enumerate(notes):
            print 'note {}:'.format(ni)
            note = parse_note(note, prevNoteDur)

            if type(note) is dict or type(note) is collections.OrderedDict: # otherwise it's a rest and we ignore it
                prevNoteDur = int(note['duration'])
            else:
                print note
                prevNoteDur = 0

            notes[ni] = note

        # notes = filter(remove_rests, notes)
        notes = [note for note in notes if (type(note) is dict or type(note) is collections.OrderedDict)]

        print 'num notes after: {}'.format(len(notes))
        # print notes

        measures[mi]['note'] = notes


    print score_json['score-partwise']['part']['measure'][0]['note']


    print debug_unparse(measures[0]['note'][0], 'note')

    with open(score_xml_out_path, 'w') as f:
        xmltodict.unparse(score_json, output=f, pretty=True)

# end