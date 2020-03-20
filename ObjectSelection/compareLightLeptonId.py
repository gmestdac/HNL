#! /usr/bin/env python

#
# Code to calculate trigger efficiency
#

import numpy as np

#
# Argument parser and logging
#
import os, argparse
argParser = argparse.ArgumentParser(description = "Argument parser")
argParser.add_argument('--isChild',  action='store_true', default=False,  help='mark as subjob, will never submit subjobs by itself')
argParser.add_argument('--year',     action='store',      default=None,   help='Select year', choices=['2016', '2017', '2018'])
argParser.add_argument('--subJob',   action='store',      default=None,   help='The number of the subjob for this sample')
argParser.add_argument('--sample',   action='store',      default=None,   help='Select sample by entering the name as defined in the conf file')
argParser.add_argument('--isTest',   action='store_true', default=False,  help='Run a small test')
argParser.add_argument('--runLocal', action='store_true', default=False,  help='use local resources instead of Cream02')
argParser.add_argument('--flavor', type=int, default=0,  help='flavor of lepton under consideration. 0 = electron, 1 = muon', choices = [0, 1])
argParser.add_argument('--dryRun',   action='store_true', default=False,  help='do not launch subjobs, only show them')
argParser.add_argument('--includeReco',   action='store_true', default=False,  help='look at the efficiency for a gen tau to be both reconstructed and identified. Currently just fills the efficiency for isolation')
argParser.add_argument('--onlyReco',   action='store_true', default=False,  help='look at the efficiency for a gen tau to be reconstructed. Currently just fills the efficiency for isolation')
args = argParser.parse_args()

#
# Change some settings if this is a test
#
if args.isTest:
    args.isChild = True
    args.sample = 'DY-ext1'
    args.subJob = '0'
    args.year = '2016'

#
# All ID's and WP we want to test
# If you want to add a new algorithm, add a line below
# Make sure all algo keys and WP have a corresponding entry in HNL.ObjectSelection.tauSelector
#
algos = {'cutbased': ['tight'],
            'leptonMVAtZq' : ['tight'],
            'leptonMVAttH' : ['tight']}

#
# Load in the sample list 
#
from HNL.Samples.sample import createSampleList, getSampleFromList
sample_list = createSampleList(os.path.expandvars('$CMSSW_BASE/src/HNL/Samples/InputFiles/compareTauIdList_'+str(args.year)+'.conf'))

#
# Submit Jobs
# TODO: Rewrite so that it checks all ID's in a single event loop instead of using more resources than needed by having jobs for every algorithm
#
if not args.isChild:

    from HNL.Tools.jobSubmitter import submitJobs
    jobs = []
    for sample in sample_list:
        if args.sample and args.sample != sample.name: continue
        for njob in xrange(sample.split_jobs):
            jobs += [(sample.name, str(njob))]

    submitJobs(__file__, ('sample', 'subJob'), jobs, argParser, jobLabel = 'compareTauID')
    exit(0)

#
#Initialize chain
#
sample = getSampleFromList(sample_list, args.sample)
chain = sample.initTree(False)
chain.year = int(args.year)
isBkgr = not 'HNL' in sample.name

#
#Set output dir
#
from HNL.Tools.helpers import makeDirIfNeeded
output_name = os.path.join(os.getcwd(), 'data', os.path.basename(__file__).split('.')[0])
if args.includeReco: output_name = os.path.join(output_name, 'includeReco')
if args.onlyReco: output_name = os.path.join(output_name, 'onlyReco')
output_name = os.path.join(output_name, sample.output)
if args.isChild:
    output_name += '/tmp_'+sample.output

print 'Getting things ready to start the event loop'

#Initialize histograms
from HNL.Tools.ROC import ROC
from HNL.Tools.efficiency import Efficiency
list_of_roc = []
list_of_var_hist = {'efficiency' : {}, 'fakerate' : {}}
for algo in algos:

    algo_wp = algos[algo]
 
    algo_bin = np.arange(0., len(algo_wp)+1., 1)
    var_roc = lambda c, i : c.var_roc[i]
    

    tot_name = output_name+'/'+ sample.name + '_'+algo+'-ROC-'+str(args.flavor)+'_' + args.subJob+'.root'
    makeDirIfNeeded(tot_name)
    list_of_roc.append(ROC(algo, var_roc, 'tmp', tot_name, algo_bin))   #TODO: Currently the way the var is implemented in Histogram class makes this a little cumbersome, change this

    #Efficiency histograms for variables
    var_hist = {'pt': [lambda c : c.pt_l, np.arange(0., 200., 10.),  ('p_T^{#tau}(offline) [GeV]' , 'Efficiency')],
                'eta': [lambda c : c.eta_l, np.arange(-2.5, 2.5, 0.5), ('#eta^{#tau}(offline) [GeV]' , 'Efficiency')]}
    
    list_of_var_hist['efficiency'][algo] = {}
    list_of_var_hist['fakerate'][algo] = {}
    for v in var_hist.keys():
        list_of_var_hist['efficiency'][algo][v] = {}
        list_of_var_hist['fakerate'][algo][v] = {}
        for wp in algo_wp:
            tot_name = output_name+'/'+ sample.name + '_efficiency-'+str(args.flavor)+'_' + args.subJob+'.root'
            list_of_var_hist['efficiency'][algo][v][wp] = Efficiency('efficiency_'+v, var_hist[v][0], var_hist[v][2], tot_name, var_hist[v][1])
            tot_name = output_name+'/'+ sample.name + '_fakerate-'+str(args.flavor)+'_' + args.subJob+'.root'
            list_of_var_hist['fakerate'][algo][v][wp] = Efficiency('fakerate_'+v, var_hist[v][0], var_hist[v][2], tot_name, var_hist[v][1], subdirs = [algo, 'fakerate_'+v])

#Determine if testrun so it doesn't need to calculate the number of events in the getEventRange
if args.isTest:
    event_range = xrange(150)
else:
    event_range = sample.getEventRange(int(args.subJob))

chain.var_roc = np.arange(0.5, 1.5, 1)

from HNL.Tools.helpers import progress
from HNL.ObjectSelection.electronSelector import isBaseElectron
from HNL.ObjectSelection.muonSelector import isBaseMuon
from HNL.ObjectSelection.leptonSelector import isTightLightLepton
from HNL.EventSelection.eventSelection import select3GenLeptons
for entry in event_range:

    chain.GetEntry(entry)
    progress(entry - event_range[0], len(event_range))

    #Loop over generator level taus if reco and id are measured
    if args.includeReco:
        if not select3GenLeptons(chain, chain): continue
        chain.pt_l = chain.l_pt[0]
        chain.eta_l = chain.l_eta[0]   
        matched_l = matchGenToReco(chain, chain.l1)
        for i, algo in enumerate(full_list): 
            for index, wp in enumerate(getWP(algo)):
                passed = False
                if args.onlyReco: 
                    passed=matched_l is not None
                else:
                    passed = matched_l is not None and isGeneralTau(chain, matched_l, algo[0], wp, algo[1], wp, algo[2], wp)
                list_of_roc[i].fillEfficiency(chain, index, passed)
                for v in list_of_var_hist['efficiency'][algo].keys():
                    list_of_var_hist['efficiency'][algo][v][wp].fill(chain, 1., passed)

#        for lepton in xrange(chain._gen_nL):
#            chain.pt_l = chain._gen_lPt[lepton]
#            chain.eta_l = chain._gen_lEta[lepton]   
#            if not isGoodGenTau(chain, lepton):    continue
#            matched_l = matchGenToReco(chain, lepton)
#            for i, algo in enumerate(full_list): 
#                for index, wp in enumerate(getWP(algo)):
#                    passed = False
#                    if args.onlyReco: 
#                        passed=matched_l is not None
#                    else:
#                        passed = matched_l is not None and isGeneralTau(chain, matched_l, algo[0], wp, algo[1], wp, algo[2], wp)
#                    list_of_roc[i].fillEfficiency(chain, index, passed)
#                    for v in list_of_var_hist['efficiency'][algo].keys():
#                        list_of_var_hist['efficiency'][algo][v][wp].fill(chain, 1., passed)

    else:
        #Loop over real taus for efficiency
        for lepton in xrange(chain._nLight):
            if chain._lFlavor[lepton] != args.flavor: continue
            if args.flavor == 0 and not isBaseElectron(chain, lepton): continue
            if args.flavor == 1 and not isBaseMuon(chain, lepton): continue

            chain.pt_l = chain._lPt[lepton]
            chain.eta_l = chain._lEta[lepton]   
        
            for i, algo in enumerate(algos): 
                # if algo[0] != 'none' and not isGeneralTau(chain, lepton, algo[0], 'none', 'againstElectron', 'none', 'againstMuon', 'none', needDMfinding=False): continue

                if chain._lIsPrompt[lepton]: 
                    for index, wp in enumerate(algos[algo]):
                        passed = isTightLightLepton(chain, lepton, algo)
                        list_of_roc[i].fillEfficiency(chain, index, passed)
                        for v in list_of_var_hist['efficiency'][algo].keys():
                            list_of_var_hist['efficiency'][algo][v][wp].fill(chain, 1., passed)

                else:
                    for index, wp in enumerate(algos[algo]):
                        passed = isTightLightLepton(chain, lepton, algo)
                        list_of_roc[i].fillMisid(chain, index, passed)
                        for v in list_of_var_hist['fakerate'][algo].keys():
                            list_of_var_hist['fakerate'][algo][v][wp].fill(chain, 1., passed)


#
# Write
#
if args.isTest: exit(0)
for r in list_of_roc:
    r.write(True)

for eff in ['efficiency', 'fakerate']:
    for a, algo in enumerate(algos): 
        for i, v in enumerate(list_of_var_hist['fakerate'][algo].keys()):
            for j, wp in enumerate(list_of_var_hist['fakerate'][algo][v].keys()):
                if a == 0 and i == 0 and j == 0:
                    list_of_var_hist[eff][algo][v][wp].write(append = False, subdirs = [algo + '-' + wp, eff+'_'+v])
                else:
                    list_of_var_hist[eff][algo][v][wp].write(append = True, subdirs = [algo + '-' + wp, eff+'_'+v]) 
