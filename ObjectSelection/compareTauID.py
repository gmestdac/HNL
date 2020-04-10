#! /usr/bin/env python

######################################################################################################
#                                                                                                    #
#   Code to calculate efficiency of different tau ID and working points                              #
#   Once can choose between regular tau ID efficiency or also including reconstruction efficiency    #
#   When testing iso efficiency, it will also loop over all combinations of lepton discriminators    #
#   to see their combined efficiency                                                                 #
#   Lepton efficiencies are treated by themselves                                                    #
#                                                                                                    #
######################################################################################################

# TODO: Think about these output, it takes way too long for them to hadd

#
# Basic imports
#
import numpy as np
from HNL.Tools.helpers import progress
from HNL.ObjectSelection.tauSelector import isGeneralTau
from HNL.ObjectSelection.tauSelector import isGoodGenTau, matchGenToReco
from HNL.EventSelection.eventSelection import select3GenLeptons

#
# Some basic parameters
# If you add to these, make sure the algorithms and working points are defined in tauSelector.py
#

iso_algo = ['MVA2017v2', 'MVA2017v2New', 'deeptauVSjets']
ele_algo = ['againstElectron', 'deeptauVSe']
mu_algo = ['againstMuon', 'deeptauVSmu']
order_of_workingpoints = ['vvvloose', 'vvloose', 'vloose', 'loose', 'medium', 'tight', 'vtight', 'vvtight']

default_iso_algo = 'deeptauVSjets'
default_ele_algo = 'deeptauVSe'
default_mu_algo = 'deeptauVSmu'


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
argParser.add_argument('--dryRun',   action='store_true', default=False,  help='do not launch subjobs, only show them')
argParser.add_argument('--includeReco',   action='store', default=None,  help='look at the efficiency for a gen tau to be both reconstructed and identified. Currently just fills the efficiency for isolation', choices = ['iso', 'noIso'])
argParser.add_argument('--discriminators', nargs='*', default=['iso', 'ele','mu'],  help='Which discriminators do you want to test?', choices = ['iso', 'ele', 'mu'])
args = argParser.parse_args()

#
# Change some settings if this is a test
#
if args.isTest:
    args.isChild = True
    args.sample = 'WZ'
    args.subJob = '0'
    args.year = '2016'

#
# Make sure we only run over iso when running reco efficiency
# In case of only reconstruction efficiency, it will choose to fill and save the default iso algorithm
# only for the None working point
# In case of reco and iso efficiency, it will run over all iso algorithms and WP as well as accompanying 
# light lepton discriminators
#
if args.includeReco is not None:
    if args.discriminators != ['iso']:
        print 'In this mode, only iso will be used. Removing "ele" and/or "mu" from the discriminator list.'
    args.discriminators = ['iso']

#
# Print out message for the user about currently selected algorithms to test
#
print '\n', 'Currently the following algorithms are selected for comparison'
if args.discriminators.count('iso'): 
    print '\n', 'Isolation:'
    for f in iso_algo: print f
if args.discriminators.count('ele'): 
    print '\n', 'Electron discriminators:'
    for f in ele_algo: print f
if args.discriminators.count('mu'): 
    print '\n', 'Muon discriminators:'
    for f in mu_algo: print f
print '\n', "If you want to change any of these, do so in compareTauID.py \n"

#
# All ID's and WP we want to test
# If you want to add a new algorithm, add a line below
# Make sure all algo keys and WP have a corresponding entry in HNL.ObjectSelection.tauSelector
#
from HNL.ObjectSelection.tauSelector import getIsoWorkingPoints, getEleWorkingPoints, getMuWorkingPoints

algos = {}
algos['iso'] = {}
for algo in iso_algo:
    algos['iso'][algo] = getIsoWorkingPoints(algo)

algos['ele'] = {}
for algo in ele_algo:
    algos['ele'][algo] = getEleWorkingPoints(algo)

algos['mu'] = {}
for algo in mu_algo:
    algos['mu'][algo] = getMuWorkingPoints(algo)

#
# Functions to find what lepton discriminators should be used with the given iso algorithm and vice versa
# Deeptau only goes with deeptau lepton discr
# The MVA's should always be used with againstMuon and againstElectron
#
def linkIsoToLep(lepton_str, iso_algo):
    if lepton_str == 'mu':
        if 'deeptau' in iso_algo: return 'deeptauVSmu'
        else: return 'againstMuon'
    elif lepton_str == 'ele':
        if 'deeptau' in iso_algo: return 'deeptauVSe'
        else: return 'againstElectron'
    return

def linkLepToIso(algo):
    if algo == 'deeptauVSe': return 'deeptauVSjets'
    elif algo == 'againstElectron': return 'MVA2017v2'
    elif algo == 'deeptauVSmu': return 'deeptauVSjets'
    elif algo == 'againstMuon': return 'MVA2017v2'
    return

#
# Load in the sample list 
#
from HNL.Samples.sample import createSampleList, getSampleFromList
sample_list = createSampleList(os.path.expandvars('$CMSSW_BASE/src/HNL/Samples/InputFiles/compareTauIdList_'+str(args.year)+'.conf'))

#
# Submit Jobs (Jobs are per sample, not split into algorithms or working points)
#
if not args.isChild:

    from HNL.Tools.jobSubmitter import submitJobs
    jobs = []
    for sample in sample_list:
        for njob in xrange(sample.split_jobs):
            jobs += [(sample.name, str(njob))]

    submitJobs(__file__, ('sample', 'subJob'), jobs, argParser, jobLabel = 'compareTauID')
    exit(0)

#
# Initialize chain
#
sample = getSampleFromList(sample_list, args.sample)
chain = sample.initTree(False)
isBkgr = not 'HNL' in sample.name

#
# Function to show what gen status' should be allowed for different types of background
# Iso discriminators should only look at the background from jets
# Electron discriminators should only look at fakes from electrons (either from leptonic
#  tau decay or natural electrons)
# Muon discriminators should only look at fakes from muons (either from leptonic
#  tau decay or natural muons)
# In case of combinations, allow all background
#
def allowedGenstatus(isoAlgo, eleAlgo, muAlgo):
    bkgr_allowed_genstatus = []
    if isoAlgo is not None:        
        bkgr_allowed_genstatus.append(6)
        if eleAlgo is not None or muAlgo is not None:        
            bkgr_allowed_genstatus.extend([1, 2, 3, 4])
    elif eleAlgo is not None:        bkgr_allowed_genstatus.extend([1, 3])
    elif muAlgo is not None:         bkgr_allowed_genstatus.extend([2, 4])
    return bkgr_allowed_genstatus

#
# Set output directories
#
reco_names = {None:'NoReco', 'iso': 'IncludeReco', 'noIso': 'OnlyReco'}

base_path = os.path.join(os.getcwd(), 'data', os.path.basename(__file__).split('.')[0], reco_names[args.includeReco])
subjobAppendix = '_subJob' + args.subJob if args.subJob else ''

if args.isChild: output_name = lambda d, a, wp: os.path.join(base_path, d, sample.output, a, str(wp), 'tmp_'+sample.output)
else: output_name = lambda d, a, wp: os.path.join(base_path, d, sample.output, a, str(wp))

print 'Initializing histograms'

#
# Initialize histograms
#
from HNL.Tools.ROC import ROC
from HNL.Tools.efficiency import Efficiency
list_of_roc = {}
list_of_var_hist = {'efficiency' : {}, 'fakerate' : {}}
var_roc = lambda c, i : c.algo_wps[i]

for discr in args.discriminators:
    #
    # ROC curves
    #
    list_of_roc[discr] = {}
    for algo in algos[discr]:
        algo_bins = np.arange(0., len(algos[discr][algo])+1., 1)
        out_path = output_name(discr, algo, 'all')+'/'+ sample.name +'_ROC' +subjobAppendix+ '.root'
        if discr != 'iso':
            list_of_roc[discr][algo] = ROC(algo, out_path, working_points=algos[discr][algo])
        else:
            list_of_roc[discr][algo] = {}
            for ele_wp in algos['ele'][linkIsoToLep('ele', algo)]:
                list_of_roc[discr][algo][ele_wp] = {}
                for mu_wp in algos['mu'][linkIsoToLep('mu', algo)]:
                    list_of_roc[discr][algo][ele_wp][mu_wp] = ROC('-'.join([algo, str(ele_wp), str(mu_wp)]), out_path, working_points=algos[discr][algo])
    #
    #Efficiency histograms for variables
    #
    var_hist = {'pt': [lambda c : c.pt_tau, np.arange(0., 200., 10.),  ('p_T^{#tau}(offline) [GeV]' , 'Efficiency')],
                'eta': [lambda c : c.eta_tau, np.arange(-2.5, 2.5, 0.5), ('#eta^{#tau}(offline) [GeV]' , 'Efficiency')]} 

    for eff_or_fake in ['efficiency', 'fakerate']:
        list_of_var_hist[eff_or_fake][discr] = {}
        for algo in algos[discr]:
            list_of_var_hist[eff_or_fake][discr][algo] = {}
            for v in var_hist.keys():
                list_of_var_hist[eff_or_fake][discr][algo][v] = {}
                if discr != 'iso' or args.includeReco == 'noIso':
                    for wp in algos[discr][algo]:
                        out_path = output_name(discr, algo, wp)+'/'+ sample.name +'_'+eff_or_fake +subjobAppendix+ '.root'
                        list_of_var_hist[eff_or_fake][discr][algo][v][wp] = Efficiency('-'.join([eff_or_fake, v, algo, str(wp)]), var_hist[v][0], var_hist[v][2], out_path, var_hist[v][1])
                else:
                    for wp in algos[discr][algo]:
                        out_path = output_name(discr, algo, wp)+'/'+ sample.name +'_'+eff_or_fake +subjobAppendix+ '.root'
                        list_of_var_hist[eff_or_fake][discr][algo][v][wp] = {}
                        for ele_wp in algos['ele'][linkIsoToLep('ele', algo)]:
                            list_of_var_hist[eff_or_fake][discr][algo][v][wp][ele_wp] = {}
                            for mu_wp in algos['mu'][linkIsoToLep('mu', algo)]:
                                list_of_var_hist[eff_or_fake][discr][algo][v][wp][ele_wp][mu_wp] = Efficiency('-'.join([eff_or_fake, v, algo, str(wp), str((ele_wp, mu_wp))]), var_hist[v][0], var_hist[v][2], out_path, var_hist[v][1])
            
#
# Determine if testrun so it doesn't need to calculate the number of events in the getEventRange
#
if args.isTest:
    event_range = xrange(150)
else:
    event_range = sample.getEventRange(int(args.subJob))

#
# Run over events
#
for entry in event_range:

    chain.GetEntry(entry)
    progress(entry - event_range[0], len(event_range))

    #
    # If reco efficiency should be included, we start from genuine generator level taus and match
    # these to reco taus
    #
    if args.includeReco is not None:
        for lepton in xrange(chain._gen_nL):

            chain.pt_tau = chain._gen_lPt[lepton]
            chain.eta_tau = chain._gen_lEta[lepton]  

            if not isGoodGenTau(chain, lepton):    continue
            matched_l = matchGenToReco(chain, lepton)

            for discr in args.discriminators:
                for algo in algos[discr]: 
                    if args.includeReco == 'noIso':
                        wp = None
                        for v in list_of_var_hist['efficiency'][discr][algo].keys():
                            list_of_var_hist['efficiency'][discr][algo][v][wp].fill(chain, 1., matched_l is not None)
                    else:
                        for ele_wp in algos['ele'][linkIsoToLep('ele', algo)]:
                            for mu_wp in algos['mu'][linkIsoToLep('mu', algo)]:
                                for index, wp in enumerate(algos[discr][algo]):
                                    wp_passed = matched_l is not None and isGeneralTau(chain, matched_l, algo, wp, linkIsoToLep('ele', algo), ele_wp, linkIsoToLep('mu', algo), mu_wp, needDMfinding=False)
                                    for v in list_of_var_hist['efficiency'][discr][algo].keys():
                                        list_of_var_hist['efficiency'][discr][algo][v][wp][ele_wp][mu_wp].fill(chain, 1., wp_passed)

    else:
        #
        #Loop over reco taus for efficiency
        #
        for lepton in xrange(chain._nLight, chain._nL):
            
            chain.pt_tau = chain._lPt[lepton]
            chain.eta_tau = chain._lEta[lepton]   
            
            for discr in args.discriminators:
                for algo in algos[discr]: 
                    if discr == 'iso' and not isGeneralTau(chain, lepton, algo, None, linkIsoToLep('ele', algo), None, linkIsoToLep('mu', algo), None, needDMfinding=False): continue
                    elif discr != 'iso' and not isGeneralTau(chain, lepton, linkLepToIso(algo), None, default_ele_algo, None, default_mu_algo, None, needDMfinding=True): continue

                    #
                    # Real taus
                    #
                    if chain._tauGenStatus[lepton] == 5:
                        if discr != 'iso':
                            passed = []
                            for index, wp in enumerate(algos[discr][algo]):
                                wp_passed = None
                                if discr == 'ele': wp_passed = isGeneralTau(chain, lepton, default_iso_algo, None, algo, wp, default_mu_algo, None)
                                elif discr == 'mu': wp_passed = isGeneralTau(chain, lepton, default_iso_algo, None, default_ele_algo, None, algo, None)
                                passed.append(wp_passed)
                                for v in list_of_var_hist['efficiency'][discr][algo].keys():
                                    list_of_var_hist['efficiency'][discr][algo][v][wp].fill(chain, 1., wp_passed)
                            list_of_roc[discr][algo].fillEfficiency(passed)
                        else:
                            for ele_wp in algos['ele'][linkIsoToLep('ele', algo)]:
                                for mu_wp in algos['mu'][linkIsoToLep('mu', algo)]:
                                    passed = []
                                    for index, wp in enumerate(algos[discr][algo]):
                                        wp_passed = isGeneralTau(chain, lepton, algo, wp, linkIsoToLep('ele', algo), ele_wp, linkIsoToLep('mu', algo), mu_wp, needDMfinding=False)
                                        passed.append(wp_passed)
                                        for v in list_of_var_hist['efficiency'][discr][algo].keys():
                                            list_of_var_hist['efficiency'][discr][algo][v][wp][ele_wp][mu_wp].fill(chain, 1., wp_passed)
                                    list_of_roc[discr][algo][ele_wp][mu_wp].fillEfficiency(passed)

                    #
                    # Fake taus
                    #
                    else:
                        if discr == 'ele' and chain._tauGenStatus[lepton] in allowedGenstatus(None, algo, None):
                            passed = []
                            for index, wp in enumerate(algos[discr][algo]):
                                wp_passed = isGeneralTau(chain, lepton, default_iso_algo, None, algo, wp, default_mu_algo, None)
                                passed.append(wp_passed)
                                for v in list_of_var_hist['fakerate'][discr][algo].keys():
                                    list_of_var_hist['fakerate'][discr][algo][v][wp].fill(chain, 1., wp_passed)
                            list_of_roc[discr][algo].fillMisid(passed)
                        elif discr == 'mu' and chain._tauGenStatus[lepton] in allowedGenstatus(None, None, algo):
                            passed = []
                            for index, wp in enumerate(algos[discr][algo]):
                                wp_passed = isGeneralTau(chain, lepton, default_iso_algo, None, default_ele_algo, None, algo, None)
                                passed.append(wp_passed)
                                for v in list_of_var_hist['fakerate'][discr][algo].keys():
                                    list_of_var_hist['fakerate'][discr][algo][v][wp].fill(chain, 1., wp_passed)
                            list_of_roc[discr][algo].fillMisid(passed)
                        elif discr == 'iso':
                            for ele_wp in algos['ele'][linkIsoToLep('ele', algo)]:
                                for mu_wp in algos['mu'][linkIsoToLep('mu', algo)]:
                                    if chain._tauGenStatus[lepton] not in allowedGenstatus(algo, ele_wp, mu_wp): continue
                                    passed = []
                                    for index, wp in enumerate(algos[discr][algo]):
                                        wp_passed = isGeneralTau(chain, lepton, algo, wp, linkIsoToLep('ele', algo), ele_wp, linkIsoToLep('mu', algo), mu_wp, needDMfinding=False)
                                        passed.append(wp_passed)
                                        for v in list_of_var_hist['fakerate'][discr][algo].keys():
                                            list_of_var_hist['fakerate'][discr][algo][v][wp][ele_wp][mu_wp].fill(chain, 1., wp_passed)
                                    list_of_roc[discr][algo][ele_wp][mu_wp].fillMisid(passed)


#
# Write
#
if args.isTest: exit(0)
print 'Saving output'

for discr in args.discriminators:

    #
    # Save ROC
    #
    if args.includeReco is None:
        if discr != 'iso':
            for ir, r in enumerate(list_of_roc[discr].values()):
                append_roc = ir != 0
                r.write(append_roc)
        else:
            for ar, algo in enumerate(algos[discr].keys()): 
                for kr, ele_wp in enumerate(algos['ele'][linkIsoToLep('ele', algo)]):
                    for ir, r in enumerate(list_of_roc[discr][algo][ele_wp].values()):
                        if ir == 0 and kr == 0 and ar == 0:
                            append_roc = False
                        else:
                            append_roc = True
                        r.write(append_roc)

    #
    # Save efficiencies and fake rates as function of variables
    #
    for eff in ['efficiency', 'fakerate']:
        for a, algo in enumerate(algos[discr].keys()): 
            for i, v in enumerate(list_of_var_hist[eff][discr][algo].keys()):
                for j, wp in enumerate(list_of_var_hist[eff][discr][algo][v].keys()):
                    if args.includeReco == 'noIso' and wp is not None: continue
                    if discr != 'iso' or args.includeReco == 'noIso':
                        if a == 0 and i == 0 and j == 0:
                            list_of_var_hist[eff][discr][algo][v][wp].write(append = False, name = eff, subdirs = [v, algo + '-' + str(wp)])
                        else:
                            list_of_var_hist[eff][discr][algo][v][wp].write(append = True, name = eff, subdirs = [v, algo + '-' + str(wp)])
                    else:
                        for k, ele_wp in enumerate(algos['ele'][linkIsoToLep('ele', algo)]):
                            for l, mu_wp in enumerate(algos['mu'][linkIsoToLep('mu', algo)]):
                                if a == 0 and i == 0 and j == 0 and k == 0 and l == 0:
                                    list_of_var_hist[eff][discr][algo][v][wp][ele_wp][mu_wp].write(append = False, name = eff, subdirs = [v, algo + '-' + str((ele_wp, mu_wp))])
                                else:
                                    list_of_var_hist[eff][discr][algo][v][wp][ele_wp][mu_wp].write(append = True, name = eff, subdirs = [v, algo + '-' + str((ele_wp, mu_wp))])

print 'Finished'