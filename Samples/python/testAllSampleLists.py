from HNL.Samples.sample import Sample, createSampleList
from HNL.Tools.helpers import isValidRootFile, makeDirIfNeeded
import glob
import os

list_of_samplelists = glob.glob(os.path.expandvars('$CMSSW_BASE/src/HNL/Samples/InputFiles/*conf'))

for sl in list_of_samplelists:
    name = sl.split('/')[-1].split('.')[0]
    print 'Checking '+name
    out_name = os.path.expandvars('$CMSSW_BASE/src/HNL/Samples/InputFiles/InputFileTests/'+name+'.txt')
    makeDirIfNeeded(out_name)
    out_file = open(out_name, 'w')
    sample_list = createSampleList(sl, True)
    for sample in sample_list:
        try:
            chain = sample.initTree(needhcount = False)
        except:
            out_file.write('Problem in '+sample.name + '\n')
    
    out_file.close()
