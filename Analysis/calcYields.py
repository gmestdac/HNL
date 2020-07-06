#! /usr/bin/env python

#
#       Code to calculate signal and background yields
#

import numpy as np
from HNL.Tools.histogram import Histogram
import ROOT

#
# Argument parser and logging
#
import os, argparse
argParser = argparse.ArgumentParser(description = "Argument parser")
argParser.add_argument('--isChild',  action='store_true', default=False,  help='mark as subjob, will never submit subjobs by itself')
argParser.add_argument('--year',     action='store',      default=None,   help='Select year', choices=['2016', '2017', '2018'])
argParser.add_argument('--sample',   action='store',      default=None,   help='Select sample by entering the name as defined in the conf file')
argParser.add_argument('--subJob',   action='store',      default=None,   help='The number of the subjob for this sample')
argParser.add_argument('--isTest',   action='store_true', default=False,  help='Run a small test')
argParser.add_argument('--runLocal', action='store_true', default=False,  help='use local resources instead of Cream02')
argParser.add_argument('--dryRun',   action='store_true', default=False,  help='do not launch subjobs, only show them')
argParser.add_argument('--masses', type=int, nargs='*',  help='Only run or plot signal samples with mass given in this list')
argParser.add_argument('--flavor', action='store', default='',  help='Which coupling should be active?' , choices=['tau', 'e', 'mu', '2l', ''])
argParser.add_argument('--coupling', type = float, action='store', default=0.01,  help='Coupling of the sample')
argParser.add_argument('--signalOnly', action='store_true', default=False,  help='Only launch jobs with signal samples')
argParser.add_argument('--backgroundOnly', action='store_true', default=False,  help='Only launch jobs with signal samples')
argParser.add_argument('--noskim', action='store_true', default=False,  help='Use no skim sample list')
argParser.add_argument('--makePlots', action='store_true', default=False,  help='make plots')

argParser.add_argument('--noTextFiles',   action='store_true', default=False,  help='make text files containing the number of events per category and sample')
argParser.add_argument('--noBarCharts',   action='store_true', default=False,  help='make bar charts containing the number of events per category and sample')
argParser.add_argument('--noPieCharts',   action='store_true', default=False,  help='make pie charts containing the number of events per category and sample')
argParser.add_argument('--noCutFlow',   action='store_true', default=False,  help='print the cutflow')
argParser.add_argument('--noSearchRegions',   action='store_true', default=False,  help='plot Search Regions')
argParser.add_argument('--groupSamples',   action='store_true', default=False,  help='plot Search Regions')

argParser.add_argument('--oldAnalysisCuts',   action='store_true', default=False,  help='apply the cuts as in AN 2017-014')
argParser.add_argument('--massRegion',   action='store', default=None,  help='apply the cuts of high or low mass regions, use "all" to run both simultaniously', choices=['high', 'low', 'all'])
argParser.add_argument('--message', type = str, default=None,  help='Add a file with a message in the plotting folder')
argParser.add_argument('--makeDataCards', type = str, default=None,  help='Make data cards of the data you have', choices=['shapes', 'cutAndCount'])
argParser.add_argument('--rescaleSignal', type = float,  action='store', default=None,  help='Enter desired signal coupling squared')
args = argParser.parse_args()

#
# Change some settings if this is a test
#
if args.isTest:
    args.isChild = True

    if args.sample is None: args.sample = 'DYJetsToLL-M-50' if not args.signalOnly else 'HNL-tau-m40'
    args.subJob = '0'
    args.year = '2016'

#
# Load in the sample list 
#
from HNL.Samples.sampleManager import SampleManager
if args.noskim:
    skim_str = 'noskim'
else:
    skim_str = 'Old' if args.oldAnalysisCuts else 'Reco'

sample_manager = SampleManager(args.year, skim_str, 'yields_'+str(args.year))
# sample_manager = SampleManager(args.year, skim_str, 'skimlist_2016')

#
# function to have consistent categories in running and plotting
#
from HNL.EventSelection.eventCategorization import CATEGORIES, SUPER_CATEGORIES
from HNL.EventSelection.eventCategorization import CATEGORY_TEX_NAMES
def listOfCategories():
    return CATEGORIES


#
# Extra imports if dividing by search region
#
from HNL.EventSelection.searchRegions import *

mass_regions = []
srm = {}
if args.massRegion is None:
    mass_regions.append('general')
    srm['general'] = SearchRegionManager('general')
elif args.massRegion == 'low':
    mass_regions.append('lowMass')
    srm['lowMass'] = SearchRegionManager('oldAN_lowMass')
elif args.massRegion == 'high':
    mass_regions.append('highMass')
    srm['highMass'] = SearchRegionManager('oldAN_highMass')
elif args.massRegion == 'all':
    mass_regions.append('lowMass')
    mass_regions.append('highMass')
    srm['lowMass'] = SearchRegionManager('oldAN_lowMass')
    srm['highMass'] = SearchRegionManager('oldAN_highMass')

#
#   Code to process events
#
if not args.makePlots and args.makeDataCards is None:
    #
    # Submit subjobs
    #
    if not args.isChild:
        from HNL.Tools.jobSubmitter import submitJobs
        jobs = []
        for sample_name in sample_manager.sample_names:
            print sample_name
            if args.sample and args.sample not in sample_name: continue
            if args.signalOnly and not 'HNL' in sample_name: continue
            if args.backgroundOnly and 'HNL' in sample_name: continue
            if 'HNL' in sample_name and not 'HNL-'+args.flavor in sample_name: continue
            sample = sample_manager.getSample(sample_name)
            if args.masses is not None and 'HNL' in sample.name and not any([str(m) in sample.name for m in args.masses]): continue
            for njob in xrange(sample.split_jobs):
                jobs += [(sample.name, str(njob))]

        submitJobs(__file__, ('sample', 'subJob'), jobs, argParser, jobLabel = 'calcYields')
        exit(0)

    #
    # Load in sample and chain
    #
    sample = sample_manager.getSample(args.sample)
    chain = sample.initTree(needhcount = False)

    #
    # Import and create cutter to provide cut flow
    #
    from HNL.EventSelection.cutter import Cutter
    cutter = Cutter(chain = chain)

    if args.isTest:
        max_events = 20000
        event_range = xrange(max_events) if max_events < len(sample.getEventRange(args.subJob)) else sample.getEventRange(args.subJob)
    else:
        event_range = sample.getEventRange(args.subJob)    

    chain.HNLmass = sample.getMass()
    chain.year = int(args.year)

    #
    # Get luminosity weight
    #
    from HNL.Weights.lumiweight import LumiWeight
    if args.noskim:
        lw = LumiWeight(sample, sample_manager)

    from HNL.EventSelection.eventCategorization import EventCategory
    ec = EventCategory(chain)

    list_of_numbers = {}
    for mr in mass_regions:
        list_of_numbers[mr] = {}
        for c in listOfCategories():
            list_of_numbers[mr][c] = {}
            for sr in xrange(1, srm[mr].getNumberOfSearchRegions()+1):
                list_of_numbers[mr][c][sr] = {}
                for prompt_str in ['prompt', 'nonprompt', 'total']:
                    list_of_numbers[mr][c][sr][prompt_str] = Histogram('_'.join([str(c), str(sr)]), lambda c: 0.5, ('', 'Events'), np.arange(0., 2., 1.))

    subjobAppendix = 'subJob' + args.subJob if args.subJob else ''
    selection_str = 'OldSel' if args.oldAnalysisCuts else 'NewCuts'

    def getOutputName(mass_str, prompt_str):
        if not args.isTest:
            output_name = os.path.join(os.getcwd(), 'data', __file__.split('.')[0], selection_str, mass_str, sample.output, prompt_str)
        else:
            output_name = os.path.join(os.getcwd(), 'data', 'testArea', __file__.split('.')[0], selection_str, mass_str, sample.output, prompt_str)

        if args.isChild:
            output_name += '/tmp_'+sample.output

        output_name += '/'+ sample.name +'_events_' +subjobAppendix+ '.root'
        return output_name

    #
    # Loop over all events
    #
    from HNL.Tools.helpers import progress
    from HNL.EventSelection.eventSelection import select3Leptons, select3GenLeptons, passBaseCutsAN2017014, passBaseCuts, lowMassCuts, highMassCuts, calculateKinematicVariables, containsOSSF
    from HNL.EventSelection.signalLeptonMatcher import SignalLeptonMatcher
    from HNL.Triggers.triggerSelection import applyCustomTriggers, listOfTriggersAN2017014
    from HNL.ObjectSelection.leptonSelector import isFOLepton, isTightLepton
    print 'tot_range', len(event_range)
    for entry in event_range:
        
        chain.GetEntry(entry)
        progress(entry - event_range[0], len(event_range))

        if args.noskim: chain.weight = lw.getLumiWeight()
        else: chain.weight = chain.lumiweight

        cutter.cut(True, 'total')

        #Triggers
        if args.oldAnalysisCuts:
            if not cutter.cut(applyCustomTriggers(listOfTriggersAN2017014(chain)), 'pass_triggers'): continue

        #Selecting 3 leptons
        if not args.oldAnalysisCuts:
            if not cutter.cut(select3Leptons(chain, chain, light_algo = 'leptonMVAtop', cutter=cutter, workingpoint = 'medium'), '3_tight_leptons'):   continue   
        else:   
            if not cutter.cut(select3Leptons(chain, chain, no_tau=True, light_algo = 'cutbased', cutter=cutter), '3_tight_leptons'):   continue   

        # chain.category will be needed in passBaseCutsAN2017014
        chain.category = ec.returnCategory()

        #Check if baseline selection passed, needs to be done after category assignment due to pt cuts dependency on it
        if not args.oldAnalysisCuts:
            if not passBaseCuts(chain, chain, cutter): continue
        else:   
            if not passBaseCutsAN2017014(chain, chain, cutter): continue

        calculateKinematicVariables(chain, chain)

        nprompt = 0
        for index in [chain.l1, chain.l2, chain.l3]:
            if chain._lIsPrompt[index]: nprompt += 1
        
        prompt_str = 'prompt' if nprompt == 3 else 'nonprompt'

        # print nprompt, prompt_str, chain.M3l, chain.minMossf

        if 'general' in mass_regions:
            chain.search_region = srm['general'].getSearchRegion(chain)
            list_of_numbers['general'][ec.returnCategory()][chain.search_region][prompt_str].fill(chain, chain.weight)
            list_of_numbers['general'][ec.returnCategory()][chain.search_region]['total'].fill(chain, chain.weight)

        if 'lowMass' in mass_regions and lowMassCuts(chain, chain, cutter):
            chain.search_region = srm['lowMass'].getSearchRegion(chain)
            list_of_numbers['lowMass'][ec.returnCategory()][chain.search_region][prompt_str].fill(chain, chain.weight)
            list_of_numbers['lowMass'][ec.returnCategory()][chain.search_region]['total'].fill(chain, chain.weight)
 
        if 'highMass' in mass_regions and highMassCuts(chain, chain, cutter):
            chain.search_region = srm['highMass'].getSearchRegion(chain)
            list_of_numbers['highMass'][ec.returnCategory()][chain.search_region][prompt_str].fill(chain, chain.weight)
            list_of_numbers['highMass'][ec.returnCategory()][chain.search_region]['total'].fill(chain, chain.weight)

    for mr in mass_regions:                
        for prompt_str in ['prompt', 'nonprompt', 'total']:
        # for prompt_str in ['total']:
            for i, c_h in enumerate(list_of_numbers[mr].keys()):
                for j, sr_h in enumerate(list_of_numbers[mr][c_h].values()):
                    output_name = getOutputName(mr, prompt_str)
                    if i == 0 and j == 0:
                        sr_h[prompt_str].write(output_name)
                    else:
                        sr_h[prompt_str].write(output_name, append=True)

        cutter.saveCutFlow(getOutputName(mr, 'total'))

#
# Merge if needed
#
else:
    from HNL.Tools.mergeFiles import merge
    import glob
    import os
    from HNL.Tools.helpers import getObjFromFile
    from HNL.Plotting.plot import Plot
    from HNL.EventSelection.eventCategorization import CATEGORY_NAMES, ANALYSIS_CATEGORIES

    #
    # Throw some exceptions if needed
    #
    if args.massRegion == 'all':
        raise RuntimeError('The option "all" is not supported in plotting. Please make a choice between low, high or None')

    mass_dict = {None: 'general', 'low':'lowMass', 'high': 'highMass'}
    selection_str = 'OldSel' if args.oldAnalysisCuts else 'NewCuts'
    mass_str = mass_dict[args.massRegion]

    if not args.isTest:
        base_path = os.path.join(os.getcwd(), 'data', __file__.split('.')[0], selection_str, mass_str)
    else:
        base_path = os.path.join(os.getcwd(), 'data', 'testArea', __file__.split('.')[0], selection_str, mass_str)
    in_files = glob.glob(os.path.join(base_path, '*', '*'))
    for f in in_files:
        if '.txt' in f or '.root' in f: continue
        merge(f)

    def mergeValues(values_to_merge, errors_to_merge):
        if len(values_to_merge) != len(errors_to_merge):
            raise RuntimeError('length of both input arrays should be the same. Now they are: len(values) = '+str(len(values_to_merge)) + ' and len(errors) = '+str(len(errors_to_merge)))
        out_val, out_err = (values_to_merge[0], errors_to_merge[0])
        if len(values_to_merge) > 1:
            for val, err in zip(values_to_merge[1:], errors_to_merge[1:]):
                out_val += val
                out_err = np.sqrt(out_err ** 2 + err ** 2)
        return out_val, out_err

    #
    # Gather all the files
    #
    list_of_values = {'signal' : {}, 'bkgr' : {}}
    list_of_errors = {'signal' : {}, 'bkgr' : {}}
    x_names = [CATEGORY_TEX_NAMES[i] for i in CATEGORIES]


    #Gather sample names
    processed_outputs = set()
    signal_names = []
    bkgr_names = []
    for sample_name in sample_manager.sample_names:
        sample = sample_manager.getSample(sample_name)
        if sample.output in processed_outputs: continue     #Current implementation of sample lists would cause double counting otherwise 
        processed_outputs.add(sample.output)
        is_signal = True if 'HNL' in sample.output else False
        if args.signalOnly and not is_signal: continue
        if args.backgroundOnly and is_signal: continue
        if 'HNL' in sample.name and not 'HNL-'+args.flavor in sample.name: continue
        if args.masses is not None and is_signal and not any([str(m) == sample.output.rsplit('-m')[-1] for m in args.masses]): continue

        print sample.output
        if is_signal: 
            signal_names.append(sample.output)
        else:
            bkgr_names.append(sample.output)
    
    #Loading in signal

    for signal in signal_names:
        print 'Loading', signal

        path_name = os.path.join(base_path, signal, 'total/events.root')

        list_of_values['signal'][signal] = {}
        list_of_errors['signal'][signal] = {}
        for c in listOfCategories():
            list_of_values['signal'][signal][c] = {}
            list_of_errors['signal'][signal][c] = {}
            for sr in xrange(1, srm[mass_str].getNumberOfSearchRegions()+1):
                tmp_hist = getObjFromFile(path_name, '_'.join([str(c), str(sr)])+'/'+'_'.join([str(c), str(sr)]))
                #Rescale if requested
                if args.rescaleSignal is not None:
                    tmp_hist.Scale(args.rescaleSignal/(args.coupling**2))
                list_of_values['signal'][signal][c][sr]= tmp_hist.GetBinContent(1)
                list_of_errors['signal'][signal][c][sr]= tmp_hist.GetBinError(1)

    #Loading in background

    if args.groupSamples:
        background_collection = sample_manager.sample_groups.keys()
    else:
        background_collection = [b for b in bkgr_names]

    for b in background_collection:
        list_of_values['bkgr'][b] = {}
        list_of_errors['bkgr'][b] = {}
        for c in listOfCategories():
            list_of_values['bkgr'][b][c] = {}
            list_of_errors['bkgr'][b][c] = {}
            for sr in xrange(1, srm[mass_str].getNumberOfSearchRegions()+1):
                list_of_values['bkgr'][b][c][sr] = 0.
                list_of_errors['bkgr'][b][c][sr] = 0.

    for bkgr in bkgr_names:
        print 'Loading', bkgr

        path_name_total = os.path.join(base_path, bkgr, 'total/events.root')
        path_name_prompt = os.path.join(base_path, bkgr, 'prompt/events.root')
        path_name_nonprompt = os.path.join(base_path, bkgr, 'nonprompt/events.root')

        for c in listOfCategories():
            for sr in xrange(1, srm[mass_str].getNumberOfSearchRegions()+1):
                if args.groupSamples:
                    # print path_name_prompt
                    tmp_hist_prompt = getObjFromFile(path_name_prompt, '_'.join([str(c), str(sr)])+'/'+'_'.join([str(c), str(sr)]))
                    tmp_hist_nonprompt = getObjFromFile(path_name_nonprompt, '_'.join([str(c), str(sr)])+'/'+'_'.join([str(c), str(sr)]))
                    sg = [sk for sk in sample_manager.sample_groups.keys() if bkgr in sample_manager.sample_groups[sk]][0]
                    if bkgr == 'DY':
                        list_of_values['bkgr']['XG'][c][sr] += tmp_hist_prompt.GetBinContent(1) 
                        list_of_errors['bkgr']['XG'][c][sr] = np.sqrt(list_of_errors['bkgr'][sg][c][sr] ** 2 + tmp_hist_prompt.GetBinError(1) ** 2)
                        list_of_values['bkgr']['non-prompt'][c][sr] += tmp_hist_nonprompt.GetBinContent(1) 
                        list_of_errors['bkgr']['non-prompt'][c][sr] = np.sqrt(list_of_errors['bkgr']['non-prompt'][c][sr] ** 2 + tmp_hist_nonprompt.GetBinError(1) ** 2)   
                    elif sg == 'non-prompt':
                        list_of_values['bkgr'][sg][c][sr] += tmp_hist_nonprompt.GetBinContent(1) 
                        list_of_errors['bkgr'][sg][c][sr] = np.sqrt(list_of_errors['bkgr'][sg][c][sr] ** 2 + tmp_hist_nonprompt.GetBinError(1) ** 2)
                    else:
                        list_of_values['bkgr'][sg][c][sr] += tmp_hist_prompt.GetBinContent(1) 
                        list_of_errors['bkgr'][sg][c][sr] = np.sqrt(list_of_errors['bkgr'][sg][c][sr] ** 2 + tmp_hist_prompt.GetBinError(1) ** 2)
                        list_of_values['bkgr']['non-prompt'][c][sr] += tmp_hist_nonprompt.GetBinContent(1) 
                        list_of_errors['bkgr']['non-prompt'][c][sr] = np.sqrt(list_of_errors['bkgr']['non-prompt'][c][sr] ** 2 + tmp_hist_nonprompt.GetBinError(1) ** 2)
                    # if sr == 3 and c in [11, 13, 14]:
                    #     print c, list_of_values['bkgr'][sg][c][sr], list_of_errors['bkgr']['non-prompt'][c][sr], tmp_hist_prompt.GetBinContent(1), tmp_hist_nonprompt.GetBinContent(1), tmp_hist_prompt.GetBinError(1), tmp_hist_nonprompt.GetBinError(1)
                    #     print list_of_values['bkgr']['non-prompt'][c][sr], list_of_errors['bkgr']['non-prompt'][c][sr]
                else:
                    tmp_hist_total = getObjFromFile(path_name_total, '_'.join([str(c), str(sr)])+'/'+'_'.join([str(c), str(sr)]))
                    list_of_values['bkgr'][bkgr][c][sr]= tmp_hist_total.GetBinContent(1)
                    list_of_errors['bkgr'][bkgr][c][sr]= tmp_hist_total.GetBinError(1)

    #
    # Add some grouped search regions for easier access
    #
    for sn in signal_names + background_collection:
        is_signal_str = 'signal' if sn in signal_names else 'bkgr'
        for c in listOfCategories():
            for group_name in srm[mass_str].getListOfSearchRegionGroups():
                values_to_merge = [list_of_values[is_signal_str][sn][c][v] for v in srm[mass_str].getGroupValues(group_name)]
                errors_to_merge = [list_of_errors[is_signal_str][sn][c][v] for v in srm[mass_str].getGroupValues(group_name)]
                list_of_values[is_signal_str][sn][c][group_name], list_of_errors[is_signal_str][sn][c][group_name] = mergeValues(values_to_merge, errors_to_merge)
            values_to_merge = [list_of_values[is_signal_str][sn][c][v] for v in range(1, srm[mass_str].getNumberOfSearchRegions()+1)]
            errors_to_merge = [list_of_errors[is_signal_str][sn][c][v] for v in range(1, srm[mass_str].getNumberOfSearchRegions()+1)]
            list_of_values[is_signal_str][sn][c]['total'], list_of_errors[is_signal_str][sn][c]['total'] = mergeValues(values_to_merge, errors_to_merge)

    #
    # Add some grouped categories for easier access
    #
    for sn in signal_names + background_collection:
        is_signal_str = 'signal' if sn in signal_names else 'bkgr'
        category_keys = [c for c in CATEGORIES]
        for ac in SUPER_CATEGORIES.keys():
            category_keys.append(ac)
            list_of_values[is_signal_str][sn][ac] = {}
            list_of_errors[is_signal_str][sn][ac] = {}
            for sr in list_of_values[is_signal_str][sn][1].keys():
                values_to_merge = [list_of_values[is_signal_str][sn][v][sr] for v in SUPER_CATEGORIES[ac]]
                errors_to_merge = [list_of_errors[is_signal_str][sn][v][sr] for v in SUPER_CATEGORIES[ac]]
                list_of_values[is_signal_str][sn][ac][sr], list_of_errors[is_signal_str][sn][ac][sr] = mergeValues(values_to_merge, errors_to_merge)
        


        
        #Combine all categories into 1 giant bin
        category_keys.append('total')
        list_of_values[is_signal_str][sn]['total'] = {}
        list_of_errors[is_signal_str][sn]['total'] = {}
        for sr in list_of_values[is_signal_str][sn][1].keys():
            values_to_merge = [list_of_values[is_signal_str][sn][v][sr] for v in CATEGORIES]
            errors_to_merge = [list_of_errors[is_signal_str][sn][v][sr] for v in CATEGORIES]
            list_of_values[is_signal_str][sn]['total'][sr], list_of_errors[is_signal_str][sn]['total'][sr] = mergeValues(values_to_merge, errors_to_merge)

    search_region_keys = range(1, srm[mass_str].getNumberOfSearchRegions()+1) + srm[mass_str].getListOfSearchRegionGroups() + ['total']




    from HNL.Tools.helpers import makePathTimeStamped
    from HNL.Plotting.plottingTools import extraTextFormat
    from HNL.Tools.helpers import getObjFromFile, rootFileContent, makeDirIfNeeded, tab


    destination = makePathTimeStamped(os.path.expandvars('$CMSSW_BASE/src/HNL/Analysis/data/Results/calcYields/'+selection_str+'/'+mass_str+'/'+args.flavor))

    coupling_squared = args.coupling**2 if args.rescaleSignal is None else args.rescaleSignal

    if args.makeDataCards is not None:
        from HNL.Stat.combineTools import makeDataCard

        #
        # If we just want cut and count without shapes, simply write datacards for everything you have
        #
        if args.makeDataCards == 'cutAndCount':
            for ac in ['total']+SUPER_CATEGORIES.keys():
                for sr in search_region_keys:
                    for s in list_of_values['signal'].keys():
                        sig_yield = list_of_values['signal'][s][ac][sr]
                        bkgr_yields = [list_of_values['bkgr'][b][ac][sr] for b in sorted(list_of_values['bkgr'].keys())]
                        bkgr_names = [b for b in sorted(list_of_values['bkgr'].keys())]
                        makeDataCard(str(ac)+'-'+str(sr), args.flavor, args.year, 0, s, bkgr_names, sig_yield, bkgr_yields, coupling_sq = coupling_squared)
        #
        # If we want to use shapes, first make shape histograms, then make datacards
        #
        elif args.makeDataCards == 'shapes':
            for ac in ['total']+SUPER_CATEGORIES.keys():
                shape_hist = {}
                n_search_regions = srm[mass_str].getNumberOfSearchRegions()

                shape_hist['data_obs'] = ROOT.TH1D('data_obs', 'data_obs', n_search_regions, 0.5, n_search_regions+0.5)
                shape_hist['data_obs'].SetBinContent(1, 1.)
                # for sample_name in list_of_values['bkgr'].keys():
                for sample_name in sample_manager.sample_groups.keys():
                    # print sample_name
                    shape_hist[sample_name] = ROOT.TH1D(sample_name, sample_name, n_search_regions, 0.5, n_search_regions+0.5)
                    for sr in xrange(1, n_search_regions+1):
                        shape_hist[sample_name].SetBinContent(sr, list_of_values['bkgr'][sample_name][ac][sr])
                        shape_hist[sample_name].SetBinError(sr, list_of_errors['bkgr'][sample_name][ac][sr])

                for sample_name in list_of_values['signal'].keys():
                    out_path = os.path.join(os.path.expandvars('$CMSSW_BASE'), 'src', 'HNL', 'Stat', 'data', 'shapes', str(args.year), args.flavor, sample_name, ac+'.shapes.root')
                    makeDirIfNeeded(out_path)
                    out_shape_file = ROOT.TFile(out_path, 'recreate')
                    n_search_regions = srm[mass_str].getNumberOfSearchRegions()
                    shape_hist[sample_name] = ROOT.TH1D(sample_name, sample_name, n_search_regions, 0.5, n_search_regions+0.5)
                    for sr in xrange(1, n_search_regions+1):
                        shape_hist[sample_name].SetBinContent(sr, list_of_values['signal'][sample_name][ac][sr])
                        shape_hist[sample_name].SetBinError(sr, list_of_errors['signal'][sample_name][ac][sr])
                    shape_hist[sample_name].Write(sample_name)
                    bkgr_names = []
                    # for bkgr_sample_name in list_of_values['bkgr'].keys()+['data_obs']:
                    for bkgr_sample_name in background_collection+['data_obs']:
                        if shape_hist[bkgr_sample_name].GetSumOfWeights() > 0 and bkgr_sample_name != 'data_obs': bkgr_names.append(bkgr_sample_name)
                        shape_hist[bkgr_sample_name].Write(bkgr_sample_name)
                    out_shape_file.Close()
                    makeDataCard(str(ac), args.flavor, args.year, 0, sample_name, bkgr_names, shapes=True, coupling_sq = coupling_squared)

    if args.makePlots:

        #
        # Make text files if requested
        #
        if not args.noTextFiles:

            from ROOT import TFile

            for sr in search_region_keys:
                makeDirIfNeeded(destination+'/Tables/table_allCategories_'+str(sr)+'.txt')
                out_file = open(destination+'/Tables/table_allCategories_'+str(sr)+'.txt', 'w')

                out_file.write('coupling squared of signal = '+str(coupling_squared) + ' \n')
                out_file.write(tab([CATEGORY_NAMES[i] for i in CATEGORIES]))

                out_file_tex = open(destination+'/Tables/table_allCategories_'+str(sr)+'_tex.txt', 'w')
                out_file_tex.write('\\begin{table}[] \n')
                out_file_tex.write("\\begin{tabular}{|"+'|'.join(['l']*len(CATEGORIES))+"|} \n")
                out_file_tex.write("\hline \n")
                out_file_tex.write('& '+'&'.join([CATEGORY_NAMES[i] for i in CATEGORIES])+' \n')
                # out_file_tex.write('& \\tau\\tau e & \\tau \\tau \\mu & \\tau e e & \\tau e \\mu & \\tau\\mu\\mu & lll & total \n')
                out_file_tex.write("\hline \n")

                for sample_name in sorted(list_of_values['signal'].keys(), key=lambda n : int(n.split('-m')[-1])):
                    out_file.write(sample_name+'\t')
                    out_file_tex.write(sample_name+' & ')

                    for c in CATEGORIES:
                        out_file.write('%4.3f' % list_of_values['signal'][sample_name][c][sr]+'\t')
                        out_file_tex.write('%4.3f' % list_of_values['signal'][sample_name][c][sr])
                        # out_file.write('%4.3f' % list_of_values['signal'][sample_name][c][sr].getHist().GetSumOfWeights()+'\t')
                        # out_file_tex.write('%4.3f' % list_of_values['signal'][sample_name][c][sr].getHist().GetSumOfWeights())
                        if not 'total' in str(c):
                            out_file_tex.write(' & ')

                    out_file.write('\n')
                    out_file_tex.write('\\\\ \hline \n')

                out_file.write('-------------------------------------------------------------------- \n')
                out_file_tex.write('\\\\ \hline \n')

                for sample_name in background_collection:
                    out_file.write(sample_name+'\t')
                    out_file_tex.write(sample_name+' & ')

                    for c in CATEGORIES:
                        out_file.write('%4.1f' % list_of_values['bkgr'][sample_name][c][sr]+'\t')
                        out_file_tex.write('%4.1f' % list_of_values['bkgr'][sample_name][c][sr])
                        if not 'total' in str(c):
                            out_file_tex.write(' & ')

                    out_file.write('\n')
                    out_file_tex.write('\\\\ \hline \n')


                out_file.close()

                out_file_tex.write('\end{tabular} \n')
                out_file_tex.write('\end{table} \n')
                out_file_tex.close()

        #
        # For bar and pie charts, no split in search regions is considered for now
        #
        if not args.noBarCharts:

            for supercat in SUPER_CATEGORIES.keys():
                #
                # Bkgr
                #
                hist_to_plot = {}
                for sample_name in background_collection:
                    # hist_to_plot[sample_name] = ROOT.TH1D(sample_name, sample_name, len(list_of_values['bkgr'][sample_name]), 0, len(list_of_values['bkgr'][sample_name]))
                    hist_to_plot[sample_name] = ROOT.TH1D(sample_name+supercat, sample_name+supercat, len(SUPER_CATEGORIES[supercat]), 0, len(SUPER_CATEGORIES[supercat]))
                    for i, c in enumerate(SUPER_CATEGORIES[supercat]):
                        # hist_to_plot[sample_name].SetBinContent(i+1, list_of_values['bkgr'][sample_name][c]['total'].getHist().GetSumOfWeights()) 
                        hist_to_plot[sample_name].SetBinContent(i+1, list_of_values['bkgr'][sample_name][c]['total']) 
                x_names = [CATEGORY_TEX_NAMES[n] for n in SUPER_CATEGORIES[supercat]]
                p = Plot(hist_to_plot.values(), hist_to_plot.keys(), name = 'Events-bar-bkgr-'+supercat, x_name = x_names, y_name = 'Events', y_log='SingleTau' in supercat)            
                p.drawBarChart(output_dir = destination+'/BarCharts', message = args.message)
                
                #
                # Signal
                #   
                hist_to_plot = []
                hist_names = []
                for sn, sample_name in enumerate(sorted(list_of_values['signal'].keys(), key=lambda k: int(k.split('-m')[-1]))):
                    # hist_to_plot.append(ROOT.TH1D(sample_name, sample_name, len(list_of_values['signal'][sample_name]), 0, len(list_of_values['signal'][sample_name])))
                    hist_to_plot.append(ROOT.TH1D(sample_name, sample_name, len(SUPER_CATEGORIES[supercat]), 0, len(SUPER_CATEGORIES[supercat])))
                    hist_names.append(sample_name)
                    for i, c in enumerate(SUPER_CATEGORIES[supercat]):
                        # hist_to_plot[sn].SetBinContent(i+1, list_of_values['signal'][sample_name][c]['total'].getHist().GetSumOfWeights()) 
                        hist_to_plot[sn].SetBinContent(i+1, list_of_values['signal'][sample_name][c]['total']) 
                x_names = [CATEGORY_TEX_NAMES[n] for n in SUPER_CATEGORIES[supercat]]
                p = Plot(hist_to_plot, hist_names, name = 'Events-bar-signal-'+supercat+'-'+args.flavor, x_name = x_names, y_name = 'Events', y_log=True)
                p.drawBarChart(output_dir = destination+'/BarCharts', parallel_bins=True, message = args.message)
        
        if not args.noPieCharts:
            example_sample = background_collection[0]
            for i, c in enumerate(sorted(list_of_values['bkgr'][example_sample].keys())):

                n_filled_hist = len([v for v in list_of_values['bkgr'].values() if v[c]['total'] > 0])    #Remove hist with 0 events, they will otherwise crash the plotting code
                if n_filled_hist == 0: continue
                hist_to_plot_pie = ROOT.TH1D(str(c)+'_pie', str(c), n_filled_hist, 0, n_filled_hist)
                sample_names = []
                j = 1
                for s in background_collection:
                    fill_val = list_of_values['bkgr'][s][c]['total']
                    if fill_val > 0:
                        hist_to_plot_pie.SetBinContent(j, fill_val)
                        sample_names.append(s)
                        j += 1

                try:
                    extra_text = [extraTextFormat(SUPERCATEGORY_TEX_NAMES[c], ypos = 0.83)] if c is not None else None
                except:
                    extra_text = [extraTextFormat('other', ypos = 0.83)] if c is not None else None
                x_names = CATEGORY_TEX_NAMES.values()
                x_names.append('total')
                p = Plot(hist_to_plot_pie, sample_names, name = 'Events_'+str(c), x_name = CATEGORY_TEX_NAMES, y_name = 'Events', extra_text = extra_text)
                p.drawPieChart(output_dir = destination+'/PieCharts', draw_percent=True, message = args.message)

        # if not args.noCutFlow:
        #     import glob
        #     all_files = glob.glob(os.path.expandvars('$CMSSW_BASE/src/HNL/EventSelection/data/eventsPerCategory/'+selection_str+'/'+mass_str+'/HNL-'+args.flavor+'*/events.root'))

        #     all_files = sorted(all_files, key = lambda k : int(k.split('/')[-2].split('.')[0].split('-m')[-1]))
        #     all_names = [k.split('/')[-1].split('.')[0] for k in all_files]

        #     from HNL.EventSelection.cutter import plotCutFlow
        #     out_name = os.path.expandvars('$CMSSW_BASE/src/HNL/EventSelection/data/Results/eventsPerCategory/'+selection_str+'/'+mass_str) +'/CutFlow/Output'
        #     plotCutFlow(all_files, out_name, all_names, ignore_weights=True)

        #
        # Produce search region plots
        #
        from decimal import Decimal
        if not args.noSearchRegions:
            from HNL.EventSelection.searchRegions import plotLowMassRegions, plotHighMassRegions

            #First we need to make histograms that have different search region on x-axis
            list_of_sr_hist = {}

            for c in CATEGORIES:
                list_of_sr_hist[c] = {'signal':{}, 'bkgr':{}}
                #
                # Bkgr
                #
                for i_name, sample_name in enumerate(background_collection):
                    list_of_sr_hist[c]['bkgr'][sample_name] = ROOT.TH1D('_'.join([sample_name, str(c)]), '_'.join([sample_name, str(c)]), srm[mass_str].getNumberOfSearchRegions(), 0.5, srm[mass_str].getNumberOfSearchRegions()+0.5)
                    for sr in xrange(1, srm[mass_str].getNumberOfSearchRegions()+1):
                        list_of_sr_hist[c]['bkgr'][sample_name].SetBinContent(sr, list_of_values['bkgr'][sample_name][c][sr])
                        list_of_sr_hist[c]['bkgr'][sample_name].SetBinError(sr, list_of_errors['bkgr'][sample_name][c][sr]) 

                #
                # Signal
                #   
                for i_name, sample_name in enumerate(list_of_values['signal'].keys()):
                    list_of_sr_hist[c]['signal'][sample_name] = ROOT.TH1D('_'.join([sample_name, str(c)]), '_'.join([sample_name, str(c)]), srm[mass_str].getNumberOfSearchRegions(), 0.5, srm[mass_str].getNumberOfSearchRegions()+0.5)
                    for sr in xrange(1, srm[mass_str].getNumberOfSearchRegions()+1):
                        list_of_sr_hist[c]['signal'][sample_name].SetBinContent(sr, list_of_values['signal'][sample_name][c][sr]) 
                        list_of_sr_hist[c]['signal'][sample_name].SetBinError(sr, list_of_errors['signal'][sample_name][c][sr])
                    if args.flavor == 'tau' and args.massRegion == 'high': list_of_sr_hist[c]['signal'][sample_name].Scale(1000)

            def mergeCategories(ac, list_of_hist, signalOrBkgr, sample_name):
                filtered_hist = [list_of_sr_hist[c][signalOrBkgr][sample_name] for c in ac]
                if len(filtered_hist) == 0:
                    raise RuntimeError("Tried to merge nonexisting categories")
                elif len(filtered_hist) == 1:
                    return filtered_hist[0]
                else:
                    new_hist = filtered_hist[0]
                    for h in filtered_hist[1:]:
                        new_hist.Add(h)
                    return new_hist

            #Now add histograms together that belong to same analysis super category
            list_of_ac_hist = {}
            for ac in ANALYSIS_CATEGORIES.keys():
                list_of_ac_hist[ac] = {'signal':[], 'bkgr':[]}

                signal_names = []
                for i_name, sample_name in enumerate(list_of_values['signal'].keys()):
                    signal_names.append(sample_name)
                    list_of_ac_hist[ac]['signal'].append(mergeCategories(ANALYSIS_CATEGORIES[ac], list_of_sr_hist, 'signal', sample_name))
                
                bkgr_names = []
                for i_name, sample_name in enumerate(background_collection):
                    bkgr_names.append(sample_name)
                    list_of_ac_hist[ac]['bkgr'].append(mergeCategories(ANALYSIS_CATEGORIES[ac], list_of_sr_hist, 'bkgr', sample_name))

                extra_text = [extraTextFormat(ac, ypos = 0.82)]
                print ac
                if args.flavor: extra_text.append(extraTextFormat('|V_{'+args.flavor+'N}|^{2} = '+'%.0E' % Decimal(str(args.coupling**2)), textsize = 0.7))
                if args.rescaleSignal is not None:
                    extra_text.append(extraTextFormat('rescaled to |V_{'+args.flavor+'N}|^{2} = '+'%.0E' % Decimal(str(args.rescaleSignal)), textsize = 0.7))
                if args.massRegion == 'low':
                    plotLowMassRegions(list_of_ac_hist[ac]['signal'], list_of_ac_hist[ac]['bkgr'], signal_names+bkgr_names, out_path = destination+'/SearchRegions/'+ac, extra_text = extra_text, sample_groups = args.groupSamples)
                if args.massRegion == 'high':
                    plotHighMassRegions(list_of_ac_hist[ac]['signal'], list_of_ac_hist[ac]['bkgr'], signal_names+bkgr_names, out_path = destination+'/SearchRegions/'+ac, extra_text = extra_text, sample_groups = args.groupSamples)

