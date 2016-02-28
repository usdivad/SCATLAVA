# SCATLAVA: Software for Computer-Assisted Transcription Learning through
# Algorithmic Variation and Analysis
# 
# by David Su, dds2135@columbia.edu


import argparse
import collections
import random
import sys
import xmltodict

note_type_to_duration = {
    '32nd': 32
}

# Default duration -> note_attrs for MusicXML construction and analysis
# NOTE: here we only support up to 32nd notes
duration_to_note_attrs = {
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
    63: {'type': '16th'}, # rounding
    64: {'type': '16th'},

    # dotted 16ths
    96: {'type': '16th', 'dot': ''},

    # 8th triplets
    84: {  # rounding
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
    126: {'type': 'eighth'}, # for rounding when tripletizing up
    127: {'type': 'eighth'}, # for rounding when tripletizing up
    128: {'type': 'eighth'},
    129: {'type': 'eighth'}, # for rounding when tripletizing up

    # dotted 8ths
    190: {'type': 'eighth', 'dot': ''},  # rounding
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
    252: {'type': 'quarter'}, # rounding
    254: {'type': 'quarter'}, # rounding
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

# Definitions for difficulty values relative to original transcription
# (so D(original_transcription) = 1)
# 


def calculate_values_for_bin(bin, bin_duration, bin_divisions): # NOTE: only does difficulty using default weights
    density = calculate_value_for_bin(bin, 'DENSITY', bin_duration, bin_divisions)
    syncopation = calculate_value_for_bin(bin, 'SYNCOPATION_KEITH', bin_duration, bin_divisions) # using keith's measure
    coordination = calculate_value_for_bin(bin, 'COORDINATION', bin_duration, bin_divisions)
    # difficulty = calculate_difficulty_from_values(density, syncopation, coordination)
    return {
        'density': density,
        'syncopation': syncopation,
        'coordination': coordination,
        # 'difficulty': difficulty
    }

# Calculate overall difficulty of a bin based on d(ensity), s(yncopation), and c(oordination) as well as corresponding w(eights)
def calculate_difficulty_from_values(d, s, c, w={'d': 0.33, 's': 0.34, 'c': 0.33}):
    return ( (d*w['d']) + (s*w['s']) + (c*w['c']) )


# Adjust the bin! (recursive)
#   bin to adjust
#   bin_duration in MusicXML format (1024 = whole note)
#   bin_divisions: total number of bins in a measure
#   target_difficulty (0 to 1, expressed as a ratio to current bin difficulty)
#   weights in form {'d': x, 's': y, 'c': z}, where x+y+z = 1 and 0 < x,y,z < 1
#   gradients in same form as above
#   i (index of current adjustment run)
def adjust_bin(bin, bin_duration, bin_divisions, target_difficulty, weights, gradients, stochastic_modifier, i=0):
    bin_values = calculate_values_for_bin(bin, bin_duration, bin_divisions)
    cur_difficulty = calculate_difficulty_from_values(bin_values['density'], bin_values['syncopation'], bin_values['coordination'], weights)
    print '{} -> values: {}, difficulty: {}'.format(i, bin_values, cur_difficulty)

    if cur_difficulty < target_difficulty:
        print 'cur_difficulty {} < target_difficulty {}; returning'.format(cur_difficulty, target_difficulty)
        return bin
    elif i > 10: # 10 pretty much guarantees we've hit the bottom
        print 'max runs exceeded! cur_difficulty={}, target_difficulty={}'.format(cur_difficulty, target_difficulty)
        return bin
    else:
        # print 'adjusting bin...'
        bin = adjust_density(bin, bin_values['density'], gradients['d'], stochastic_modifier, i)
        bin = adjust_syncopation(bin, bin_values['syncopation'], gradients['s'], stochastic_modifier, i)
        bin = adjust_coordination(bin, bin_values['coordination'], gradients['c'], stochastic_modifier, i)
        # bin = adjust_for_rests(bin)
        return adjust_bin(bin, bin_duration, bin_divisions, target_difficulty, weights, gradients, stochastic_modifier, i+1)

def adjust_density(bin, d, g, sm, i):
    # return d - g
    adjusted_bin = bin
    # adjust = random.choice([True, False])
    adjust = random.random() < sm
    if (i*g >= 1) and adjust:
        # adjusted_bin = bin[:1] # get first element only
        filtered_bin = filter_bin(adjusted_bin)
        # print filtered_bin
        # filtered_bin_size = reduce(lambda x, y: 1 if x['@default-x'] != y['@default-x'] else 0, filtered_bin, 0)
        filtered_bin_size = get_polyphonic_bin_density(filtered_bin)
        # print filtered_bin

        # always remove one note if we have more than one note
        if filtered_bin_size > 1 and len(adjusted_bin) > 1:
            bi = random.randint(1, len(adjusted_bin) - 1) # we avoid removing the first note
            adjusted_bin[bi]['rest'] = None

            # todo: adjust (reverse tripletize) if it was a triplet and now is eighth note!
            #       and adjust for rests? or that can come later
        else:
            print 'only {} elements in filtered bin (though adjusted bin has {} elements)'.format(len(filtered_bin), len(adjusted_bin))

        print 'density adjusted for run {}'.format(i)
    return adjusted_bin

def adjust_syncopation(bin, s, g, sm, i):
    # return s - g
    # dice = random.random()
    # adjust = dice < s # the more syncopated a bin already is, the greater chance of adjustment
    # adjust = True
    # adjust = random.choice([True, False])
    adjust = random.random() < sm
    adjusted_bin = bin
    # print s
    if i*g >= 1 and adjust:
        filtered_bin = filter_bin(adjusted_bin)
        first_note = adjusted_bin[0]
        first_onset_index = -1
        oi = 0
        simultaneous_first_onsets_offset = 1

        # find the first onset index
        while first_onset_index < 0 and oi < len(adjusted_bin):
            note = adjusted_bin[oi]
            if is_onset_note(note):
                first_onset_index = oi
            oi += 1

        # swap first note with first onset
        adjusted_bin = swap(adjusted_bin, 0, first_onset_index)

        # swap any simultaneous onsets corresponding to the new first onset
        while simultaneous_first_onsets_offset > 0 and first_onset_index + simultaneous_first_onsets_offset < len(adjusted_bin):
            si = first_onset_index + simultaneous_first_onsets_offset
            note = adjusted_bin[si]
            
            if is_onset_note(note):
                first_x = adjusted_bin[0]['@default-x']
                note_x = note['@default-x']
                print '{},{}'.format(first_x, note_x)
                if note_x == first_x:
                    swap(adjusted_bin, simultaneous_first_onsets_offset, si)
                    simultaneous_first_onsets_offset += 1
                else:
                    simultaneous_first_onsets_offset = -1
            else:
                simultaneous_first_onsets_offset = -1


        # some engraving prettifying
        adjusted_bin[0]['beam'] = None

        # todo: adjust subdivision? esp for 8th triplets and such

        # while ( (not is_valid_note(adjusted_bin[0])) or 'rest' in adjusted_bin[0] ) and len(adjusted_bin) > 1:
        #     adjusted_bin = adjusted_bin[1:]
        # for ni, note in enumerate(adjusted_bin):
        #     if is_valid_note(note) and 'rest' not in note:

        print 'syncopation adjusted for run {}'.format(i)
    return adjusted_bin

def adjust_coordination(bin, c, g, sm, i):
    # return c - g
    adjusted_bin = bin
    adjusted = False
    # adjust = random.choice([True, False])
    adjust = random.random() < sm
    if (i*g >= 1) and adjust:
        # make sure there are actual onsets in the bin
        filtered_bin = filter_bin(adjusted_bin)
        if len(filtered_bin) < 1:
            return adjusted_bin

        # adjust one note
        while not adjusted: 
            ni = random.randint(0, len(adjusted_bin)-1)
            note = adjusted_bin[ni]
            if is_onset_note(note):
                subsequent_onsets = filter_bin(adjusted_bin[ni:])
                previous_onsets = filter_bin(adjusted_bin[:ni])

                # change note to next note
                if len(subsequent_onsets) > 0 and len(previous_onsets) > 0: # choose between next and prev note
                    note_choices = [subsequent_onsets[0], previous_onsets[0]]
                    note = update_pitch(note, random.choice(note_choices))
                    adjusted = True
                elif len(subsequent_onsets) > 0: # next note
                    note = update_pitch(note, subsequent_onsets[0])
                    adjusted = True
                elif len(previous_onsets) > 0: # prev note
                    note = update_pitch(note, previous_onsets[0])
                    adjusted = True

                # and remove a simultaneous note
                if adjusted:
                    # remove_simultaneous_note = random.choice([True, False])
                    remove_simultaneous_note = random.random() < sm
                    # remove_simultaneous_note = True
                    if remove_simultaneous_note and ni < len(adjusted_bin)-1:
                        next_note = adjusted_bin[ni+1]
                        if is_onset_note(next_note) and next_note['@default-x'] == note['@default-x']: # simultaneous
                            adjusted_bin = adjusted_bin[:ni] + adjusted_bin[ni+1:]


            adjusted_bin[ni] = note

        print 'coordination adjusted for run {}'.format(i)
    return adjusted_bin


# scale subdivisions up by one (so 16ths -> 8th triplets)
# dummy for now
def adjust_subdivisions(bin):
    return bin

# adjust note lengths
def adjust_for_rests(bin):
    adjusted_bin = bin
    for i, note in enumerate(bin):
        print 'note {}:'.format(i)
        if is_valid_note(note):
            new_note_duration = note['duration']
            if i < len(bin)-1:
                ni = i + 1
                while is_valid_note(bin[ni]) and 'rest' in bin[ni] and ni < len(bin)-1:
                    new_note_duration += bin[ni]['duration']
                    bin[ni] = 'rest'
                    # bin[ni]['rest'] = None
                    ni += 1
                note['duration'] = new_note_duration
                bin[i] = note
    return adjusted_bin

# strip rests from bin
def filter_bin(bin):
    return filter(lambda note: is_onset_note(note), bin)

def is_onset_note(note):
    return is_valid_note(note) and 'rest' not in note

# returns size of bin, treating simultaneous onsets as ONE single note
def get_polyphonic_bin_density(bin):
    size = 0
    for i, note in enumerate(bin):
        if i == 0 or note['@default-x'] != bin[i-1]['@default-x']:
            size += 1
    return size

# swap two elements in a list
def swap(bin, i, j):
    tmp = bin[i]
    bin[i] = bin[j]
    bin[j] = tmp
    return bin

# update the pitch of note to that of note_new
def update_pitch(note, note_new):
    note['unpitched']['display-step'] = note_new['unpitched']['display-step']
    note['unpitched']['display-octave'] = note_new['unpitched']['display-octave']
    if 'notehead' in note_new:
        note['notehead'] = note_new['notehead']
        # print '{} == {}'.format(note['notehead'], note_new['notehead'])
    return note

# Augmentation of a note, given several params
def parse_note(note, prev_note, duration_min, duration_left):
    print '{} left'.format(duration_left)
    if is_valid_note(note): # otherwise it's a deleted and we ignore it

        if 'rest' in note:
            return note

        # comparing durations to prev
        duration = int(note['duration'])
        prev_note_dur = int(prev_note['duration'])
        diff = prev_note_dur - duration
        # duration_error_margin = 10
        print '{} - {} = {}'.format(prev_note_dur, duration, diff)

        # comparing note equality from prev
        same_note = False
        if 'unpitched' in note and 'unpitched' in prev_note:
            notename = to_note_name(note)
            prev_notename = to_note_name(prev_note)
            same_note = (notename == prev_notename)

        if diff > 0: #and same_note:
            print 'note of duration {} has been removed'.format(duration)
            # return 'rest'
            return diff

        # testing
        if 'dot' not in note:
            # if 'time-modification' in note:
            #     while duration < duration_min:
            #         print '{} < {}'.format(duration, duration_min)
            #         duration = int(duration * 1.5) # todo: smartly tripletize
            # else:
            #     while duration < duration_min:
            #         print '{} < {}'.format(duration, duration_min)
            #         duration = int(duration * 2)

            while duration < duration_min: #and duration > duration_left:
                print '{} < {}'.format(duration, duration_min)
                if 'time-modification' in duration_to_note_attrs[duration]:
                    duration = int(duration * 1.5)
                else:
                    duration = int(duration * 2)


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

        note.pop('@default-x', None)

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

def to_note_name(note):
    if 'unpitched' not in note:
        return 'B#0'
    unpitched = note['unpitched']
    return '{}{}'.format(unpitched['display-step'], unpitched['display-octave'])

def is_valid_note(note):
    return type(note) is dict or type(note) is collections.OrderedDict

def add_duration(x,y):
    return x+y

def note_to_rest(note):
    rest = {
        'rest': None,
        'duration': note['duration'],
        'type': note['type']
    }
    return rest

# Determine the syncopation value of a beat (bin) via one of several methods
def calculate_value_for_bin(bin, method, bin_size, bin_divisions=4, max_bin_granularity=32):
    value = 0
    granularity = max_bin_granularity / bin_divisions

    # Onset Density Measure:
    # - essentially calculates onsets over duration
    # - make sure max_bin_granularity > the max number of possible onsets you might have, otherwise value will be greater than 1
    if method == 'DENSITY':
        total_bin_duration = get_total_bin_duration(bin)
        if total_bin_duration > 0:
            # value = float(len(beat)) / total_bin_duration
            # value = value * bin_size / granularity

            # simplified calculation that accounts for rests
            value = float(len([note for note in bin if 'rest' not in note])) / granularity
    

    # Syncopation (using Keith's measure):
    # - adapted for bins as it depends on bin_size
    elif method == 'SYNCOPATION_KEITH':
        cur_duration = 0
        value = 0
        for ni, note in enumerate(bin):
            cur_note_on_beat = False
            next_note_on_beat = False
            note_duration = int(note['duration']) if is_valid_note(note) else 0
            cur_value = 0

            # is this note on the beat?
            if 'rest' not in note and cur_duration % bin_size == 0:
                cur_note_on_beat = True

            # is the next note on the beat?
            if ni < len(bin) - 1:
                next_note = bin[ni+1]
                if 'rest' not in next_note and cur_duration + note_duration % bin_size == 0:
                    next_note_on_beat = True
            else:
                next_note_on_beat = True


            # score according to keith's measure
            if next_note_on_beat:
                if cur_note_on_beat:
                    cur_value = 0
                else:
                    cur_value = 1
            else:
                if cur_note_on_beat:
                    cur_value = 2
                else:
                    cur_value = 3

            # normalize cur_value
            cur_value = float(cur_value) / 3

            # add to total value
            value += cur_value / len(bin)

            # increment current duration
            cur_duration += note_duration
    
    elif method == 'COORDINATION':
        # print bin[0].keys()
        default_xs = [note['@default-x'] if is_valid_note(note) else None for note in bin]
        # print default_xs
        # print '{} vs {}'.format(len(default_xs), len(bin))
        num_notes = len(bin)
        value = 0
        max_simultaneous_limbs = 4 # RH, RF, LH, LF

        for ni, note in enumerate(bin):
            cur_value = 0
            cur_note_name = to_note_name(note)
            next_note_name = cur_note_name
            prev_note_name = cur_note_name

            simultaneous_onsets = len(filter(lambda x: is_valid_note(note) and x == note['@default-x'], default_xs))
            # print simultaneous_onsets

            if ni < num_notes - 1:
                next_note = bin[ni+1]
                next_note_name = to_note_name(next_note)
            if ni > 0:
                prev_note = bin[ni-1]
                prev_note_name = to_note_name(prev_note)

            # score according to contextual note interdependence difficulty (CNID) measure
            if cur_note_name != next_note_name:
                cur_value += 1
            if cur_note_name != prev_note_name:
                cur_value += 1
            if prev_note_name != next_note_name and cur_value > 0:
                cur_value += 1
            cur_value += simultaneous_onsets / max_simultaneous_limbs

            # normalize score
            cur_value = float(cur_value) / 4

            # add to total value
            value += cur_value / num_notes


    return value

def get_total_bin_duration(bin):
    return reduce(add_duration, [int(note['duration']) if is_valid_note(note) else 0 for note in bin], 0)

# this is ugly and repetitive but works as a temporary measure
def calculate_overall_difficulty(measures, weights):
    overall_difficulty = 0
    for mi, measure in enumerate(measures):
        # print measure
        notes = measure['note']
        prev_note_dur = 0
        prev_note = {
            'duration': '0',
            'unpitched': {
                'display-step': 'X',
                'display-octave': '-1'
            }
        }
        duration_left = 1024 # default measure length in 4/4
        # print 'num notes before: {}'.format(len(notes))

        # measure values
        measure_density = 0
        measure_syncopation = 0
        measure_coordination = 0
        measure_difficulty_original = 0
        measure_difficulty_new = 0


        # another approach: binning
        bin_divisions = 1
        bin_duration = duration_left / bin_divisions
        cur_bin_duration = bin_duration
        bin_i = 0
        bins = [ [] for i in xrange(bin_divisions) ]

        # separate notes into bins by beat
        prev_x = 0
        for ni, note in enumerate(notes):
            if is_valid_note(note) and 'duration' in note:
                if ni < len(notes)-1 and note['@default-x'] != notes[ni+1]['@default-x']: # don't increment duration if it's simultaneous onset
                    cur_bin_duration -= int(note['duration'])
                bins[bin_i].append(note)
                prev_x = note['@default-x']
            if cur_bin_duration <= 0:
                # print cur_bin_duration
                bin_i = min(bin_i+1, len(bins)-1)

                while cur_bin_duration < 0: # in cases where a note is longer than a bin size
                    bin_i = min(bin_i+1, len(bins)-1)
                    cur_bin_duration += bin_duration

                cur_bin_duration = bin_duration

        # output analysis to validate correct binning
        for bi, bin in enumerate(bins):
            total_duration = get_total_bin_duration(bin)
            bin_density = calculate_value_for_bin(bin, 'DENSITY', bin_duration, bin_divisions)
            bin_keith = calculate_value_for_bin(bin, 'SYNCOPATION_KEITH', bin_duration, bin_divisions)
            bin_coordination = calculate_value_for_bin(bin, 'COORDINATION', bin_duration, bin_divisions)
            difficulty = calculate_difficulty_from_values(bin_density, bin_keith, bin_coordination, weights)

            measure_density += bin_density / bin_divisions
            measure_syncopation += bin_keith / bin_divisions
            measure_coordination += bin_coordination / bin_divisions
            measure_difficulty_original += difficulty / bin_divisions

            # print 'measure {} beat {}: {} notes, total_duration={}, bin_density={}, bin_keith={}, bin_coordination={}, difficulty={}'.format(mi+1, bi+1, len(bin), total_duration, bin_density, bin_keith, bin_coordination, difficulty)

        # print 'measure {} overall d={}, s={}, c={}, D={} (b={})'.format(mi+1, measure_density, measure_syncopation, measure_coordination, measure_difficulty_original, bin_divisions)

        overall_difficulty += measure_difficulty_original/len(measures)

    return overall_difficulty

# The main method, to be run with each generation of a new score
if __name__ == '__main__':

    parser = argparse.ArgumentParser(description = 'SCATLAVA: Software for Computer-Assisted Transcription Learning through Algorithmic Variation and Analysis')
    parser.add_argument('score_xml_in_path', help='the original transcription')
    parser.add_argument('score_xml_out_path', help='the generated modified score', nargs='?', default='scatlava_out.xml')
    parser.add_argument('-t', '--target_difficulty', help='0 to 1, as a ratio of original transcription\'s difficulty', default=0.5, type=float)
    parser.add_argument('-w', '--weights', help='comma-separated d,s,c. e.g. 0.2,0.1,0.7', default='0.33,0.33,0.34')
    parser.add_argument('-g', '--gradients', help='comma-separated d,s,c. e.g. 0.2,0.1,0.7', default='0.33,0.33,0.34')
    parser.add_argument('-b', '--bin_divisions', help='number of bins to divide a measure into', default=4, type=int)
    parser.add_argument('-f', '--stochastic_modifier', help='0 to 1', default=0.5, type=float)
    parser.add_argument('-a', '--analysis_only', help='flag to set analysis mode on or off', action='store_true')

    args = parser.parse_args()

    score_xml_in_path = args.score_xml_in_path
    score_xml_out_path = args.score_xml_out_path
    # difficulty_gradient = sys.argv[3] # 0 to 1.
    # minimum_difficulty = sys.argv[4]
    # target_difficulty = minimum_difficulty + difficulty_gradient
    target_difficulty = args.target_difficulty
    weights_str = args.weights
    gradients_str = args.gradients
    bin_divisions = args.bin_divisions
    stochastic_modifier = args.stochastic_modifier
    analysis_only = args.analysis_only

    # put weights in {'d': n, 's': n, 'c': n} format
    weights_arr = [float(w) for w in weights_str.split(',')]
    weights = {
        'd': weights_arr[0],
        's': weights_arr[1],
        'c': weights_arr[2]
    }

    # put gradients in {'d': n, 's': n, 'c': n} format
    gradients_arr = [float(w) for w in gradients_str.split(',')]
    gradients = {
        'd': gradients_arr[0],
        's': gradients_arr[1],
        'c': gradients_arr[2]
    }

    # calculate gradients from user_confidences


    # load input score as json
    score_xml = ''
    with open(score_xml_in_path, 'r') as f:
        score_xml = f.read()

    score_json = xmltodict.parse(score_xml)
    measures = score_json['score-partwise']['part']['measure'] # a list
    # print measures[3]
    if type(measures) != list: # 0 or 1 measures
        measures = [measures]

    duration_min = 128 # rhythmic granularity of the output score we want

    # difficulty tracking!
    # overall_difficulty_original_by_measure = 0
    # overall_difficulty_original_by_bins = 0
    # overall_difficulty_new_by_measure = 0
    # overall_difficulty_new_by_bins = 0
    overall_difficulty_original = 0
    overall_difficulty_new = 0
    
    overall_difficulty_original_by_measure = calculate_overall_difficulty(measures, weights)
    overall_difficulty_new_by_measure = 0

    # iterate through measures
    for mi, measure in enumerate(measures):
        # print measure
        notes = measure['note']
        prev_note_dur = 0
        prev_note = {
            'duration': '0',
            'unpitched': {
                'display-step': 'X',
                'display-octave': '-1'
            }
        }
        duration_left = 1024 # default measure length in 4/4
        # print 'num notes before: {}'.format(len(notes))

        # measure values
        measure_density = 0
        measure_syncopation = 0
        measure_coordination = 0
        measure_difficulty_original = 0
        measure_difficulty_new = 0


        # another approach: binning
        # bin_divisions = 4
        bin_duration = duration_left / bin_divisions
        cur_bin_duration = bin_duration
        bin_i = 0
        bins = [ [] for i in xrange(bin_divisions) ]

        # separate notes into bins by beat
        prev_x = 0
        for ni, note in enumerate(notes):
            if is_valid_note(note) and 'duration' in note:
                if ni < len(notes)-1 and note['@default-x'] != notes[ni+1]['@default-x']: # don't increment duration if it's simultaneous onset
                    cur_bin_duration -= int(note['duration'])
                bins[bin_i].append(note)
                prev_x = note['@default-x']
            if cur_bin_duration <= 0:
                # print cur_bin_duration
                bin_i = min(bin_i+1, len(bins)-1)

                while cur_bin_duration < 0: # in cases where a note is longer than a bin size
                    bin_i = min(bin_i+1, len(bins)-1)
                    cur_bin_duration += bin_duration

                cur_bin_duration = bin_duration

        # output analysis to validate correct binning
        for bi, bin in enumerate(bins):
            total_duration = get_total_bin_duration(bin)
            bin_density = calculate_value_for_bin(bin, 'DENSITY', bin_duration, bin_divisions)
            bin_keith = calculate_value_for_bin(bin, 'SYNCOPATION_KEITH', bin_duration, bin_divisions)
            bin_coordination = calculate_value_for_bin(bin, 'COORDINATION', bin_duration, bin_divisions)
            difficulty = calculate_difficulty_from_values(bin_density, bin_keith, bin_coordination, weights)

            measure_density += bin_density / bin_divisions
            measure_syncopation += bin_keith / bin_divisions
            measure_coordination += bin_coordination / bin_divisions
            measure_difficulty_original += difficulty / bin_divisions

            # print 'measure {} beat {}: {} notes, total_duration={}, bin_density={}, bin_keith={}, bin_coordination={}, difficulty={}'.format(mi+1, bi+1, len(bin), total_duration, bin_density, bin_keith, bin_coordination, difficulty)

        # print 'measure {} overall d={}, s={}, c={}, D={} (b={})'.format(mi+1, measure_density, measure_syncopation, measure_coordination, measure_difficulty_original, bin_divisions)
        # exit(0)

        # create new phrase
        if not analysis_only:
            print '\n\n...\ncreating new phrase\n...\n'
            for bi, bin in enumerate(bins):
                values = calculate_values_for_bin(bin, bin_duration, bin_divisions)
                difficulty = calculate_difficulty_from_values(values['density'], values['syncopation'], values['coordination'], weights)

                print '\n=== measure {} beat {} ==='.format(mi+1, bi+1)

                if difficulty > 0:
                    bin = adjust_bin(bin, bin_duration, bin_divisions, target_difficulty*difficulty, weights, gradients, stochastic_modifier)
                bins[bi] = bin

                # recalculate difficulty
                values = calculate_values_for_bin(bin, bin_duration, bin_divisions)
                difficulty = calculate_difficulty_from_values(values['density'], values['syncopation'], values['coordination'], weights)
                measure_difficulty_new += difficulty / bin_divisions
        # else:
        #     print 'analysis mode only: not generating new phrase'

        # new notes
        notes = []
        for bin in bins:
            notes += bin


        # # iterate through notes and adjust durations (or delete note) using parse_note()
        # for ni, note in enumerate(notes):
        #     print 'note {}:'.format(ni)
        #     # note = parse_note(note, prev_note)
        #     note = parse_note(note, {'duration': prev_note_dur}, duration_min, duration_left)

        #     if is_valid_note(note): # otherwise it's a rest and we ignore it
        #         duration = int(note['duration'])
        #         prev_note_dur = duration
        #         duration_left -= duration
        #         prev_note = note
        #     else:
        #         # print note
        #         prev_note_dur = 0
        #         # duration_left -= note
        #         # prev_note['duration'] = 0

        #     notes[ni] = note

        # # notes = filter(remove_rests, notes)
        # notes = [note for note in notes if (is_valid_note(note))]

        overall_difficulty_original += measure_difficulty_original/len(measures)
        overall_difficulty_new += measure_difficulty_new/len(measures)
        # print 'measure difficulty: {} -> {}'.format(measure_difficulty_original, measure_difficulty_new)

        # print 'num notes after: {}'.format(len(notes))
        # print notes

        measures[mi]['note'] = notes



    # print '\n\n'
    # print score_json['score-partwise']['part']['measure'][0]['note']

    # stats
    # score_json['credit']
    print '\n\nusing: {}'.format(args)
    overall_difficulty_new_by_measure = calculate_overall_difficulty(measures, weights)
    print 'overall difficulty (by bins): {} -> {} (ratio of {})'.format(overall_difficulty_original, overall_difficulty_new, float(overall_difficulty_new)/overall_difficulty_original)
    print 'overall difficulty (by measures): {} -> {} (ratio of {})'.format(overall_difficulty_original_by_measure, overall_difficulty_new_by_measure, float(overall_difficulty_new_by_measure)/overall_difficulty_original_by_measure)
    # print 'ratio to 1_original is {}; target difficulty was {}'.format(overall_difficulty_new_by_measure/0.567598824786, target_difficulty)
    print 'target_difficulty was {}'.format(target_difficulty)

    # print debug_unparse(measures[0]['note'][0], 'note')

    if not analysis_only:
        with open(score_xml_out_path, 'w') as f:
            xmltodict.unparse(score_json, output=f, pretty=True)
        print 'wrote to {}'.format(score_xml_out_path)