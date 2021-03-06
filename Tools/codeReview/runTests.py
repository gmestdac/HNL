#
#       Code to run tests of all the specified code in the repo
#       Meant as a check if I broke something before pushing all the broken stuff to github
#       TODO: Add test output like in heavyNeutrino
#

#
# Argument parser and logging
#
import os, argparse
argParser = argparse.ArgumentParser(description = "Argument parser")
argParser.add_argument('--allCombinations',  action='store_true', default=False,  help='Run code that makes long list of all arguments to be combined in tests')
args = argParser.parse_args()

#
# Functions to be used later on
#
def makeCombinations(input_dict):
    argument_list = ['']
    for k in input_dict.keys():
        renewed_argument_list = []
        for arg in argument_list:
            for entry in input_dict[k]:
                renewed_argument_list.append(arg+' '+entry)
        argument_list = renewed_argument_list
    return argument_list

def createCommandList(input_list):
    try:
        len(input_list)
    except:
        "Weird stuff going on in input_list of createCommandList. Are you sure the input_list is a list?"
    if not input_list:
        raise RuntimeError('Invalid input list for createCommandList: '+str(input_list))
    
    #No arguments given
    if len(input_list) == 1:
        return input_list
    else:
        main_command = input_list[0]
        argument_dict = {}
        for arg in input_list[1:]:
            split_arg = arg.split(' ')
            argument_dict[split_arg[0]] = []
            if len(split_arg) == 1:                             # Check if it's an argument with input
                argument_dict[split_arg[0]].append('')
                argument_dict[split_arg[0]].append(split_arg[0])
            else:
                main_arg = split_arg[0]
                argument_dict[main_arg].append('')
                for option in split_arg[1:]:
                    argument_dict[main_arg].append(' '.join([main_arg, option]))
        combinations = makeCombinations(argument_dict)

        return [' '.join([main_command, comb]) for comb in combinations]

#
# Shared constant
#
import glob
import os
import time
base_path = os.path.join(os.path.expandvars('$CMSSW_BASE'), 'src', 'HNL')


#
# Run exhaustive mode
#
if args.allCombinations:
    print '\n'
    print "This mode will form all possible combinations of all arguments for each program specified in data/input/codeToTest.conf"
    print "It is not smart, it will make every combination it can. These are potentially a lot of combinations."
    print "It is recommended to run this mode in a screen on a mlong machine."
    print "WIP"
    print '\n'
    time.sleep(2)

    input_file = 'data/input/codeToTest.conf'
    code_to_test = [line.split('#')[0].strip() for line in open(input_file)]
    code_to_test = [l.split('%') for l in code_to_test if l]

    out_name = 'data/output/codeToTest_output.txt'
    out_file = open(out_name, 'w')
    out_file.close()

    for code in code_to_test:
        combinations = createCommandList(code)
        for comb in combinations:
            # out_file.write('RUNNING '+ comb + ' \n')
            os.system('python '+os.path.join(base_path,comb) + ' >> '+out_name)

else:
    print "This mode requires input in data/input/codeToTest_custom.conf. Make sure you have done that"
    input_file = 'data/input/codeToTest_custom.conf'
    code_to_test = [line.split('#')[0].strip() for line in open(input_file)]
    code_to_test = [l for l in code_to_test if l]
    for code in code_to_test:
        print '\x1b[6;30;42m' + 'RUNNING '+ code + ' \x1b[0m'
        os.system('python '+os.path.join(base_path,code))





#
# Backup
#

# import os
# import glob
# base_path = os.path.join(os.path.expandvars('$CMSSW_BASE'), 'src', 'HNL')
# code_to_test = [line.split('#')[0].strip() for line in open('codeToTest.conf')]
# code_to_test = [l.split('%') for l in code_to_test if l]
# for code in code_to_test:
#     print code
#     # createCommandList(code)
#     # print '\x1b[6;30;42m' + 'RUNNING '+ code + ' \x1b[0m'
#     # os.system('python '+os.path.join(base_path,code))
        