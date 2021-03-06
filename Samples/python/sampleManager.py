from HNL.Samples.sample import *
import os


#
# To get load in samples, this manager is used
# There are 9 general list, containing all the available samples and cross sections  for all three years for three different types of skims (no skim, reco skim, gen skim)
# To select samples to use in a certain piece of code, you can make a list with the sample names in a "sublist"
# No need to include the extensions in the sublists, it will handle that
#

ALLOWED_SKIMS = ['noskim', 'Reco', 'Gen', 'Old']
BASE_PATH = os.path.join(os.path.expandvars('$CMSSW_BASE'), 'src', 'HNL', 'Samples', 'InputFiles')
SAMPLE_GROUPS = {
    'non-prompt': ['DY', 'WJets', 'WW', 'ST', 'TT'],
    'TT-T+X': ['ttX', 'TTG', 'TG'],
    'triboson': ['triboson'],
    'WZ': ['WZ'],
    # 'diboson': ('ZZ', 'WW', 'WZ'),
    'ZZ-H': ['ZZ', 'QCD', 'Higgs'],
    'XG': ['WG']
}


class SampleManager:


    def __init__(self, year, skim, sample_names_file):
        if not skim in ALLOWED_SKIMS:
            raise RuntimeError("skim "+skim+" not allowed in the sample manager")

        self.year = year
        self.skim = skim
        self.path = os.path.join(BASE_PATH, '_'.join(['sampleList', str(self.year), skim+'.conf']))

        sample_names_file_full = os.path.join(BASE_PATH, 'Sublists', sample_names_file+'.conf')
        self.sample_names = self.getSampleNames(sample_names_file_full)
        self.sample_list = createSampleList(self.path)
        self.sample_groups = SAMPLE_GROUPS

    def getSampleNames(self, in_file_name):
        sample_infos = [line.split('%')[0].strip() for line in open(in_file_name)]                     # Strip % comments and \n charachters
        sample_infos = [line for line in sample_infos if line] 
        sample_infos = [info for info in sample_infos if info in getListOfSampleNames(self.path)]
        # Add extension files if this is noskim
        # For the Gen and Reco skims, the skimmer already included those to be added in the final sample
        if self.skim == 'noskim':
            for info in sample_infos:
                sample_infos.extend([x for x in getListOfSampleNames(self.path) if info+'-ext' in x])
        return sample_infos

    def getSample(self, name):
        sample = getSampleFromList(self.sample_list, name)
        self.sample_list = createSampleList(self.path)
        return sample

    def makeLumiClusters(self):
        self.lumi_clusters = {}
        for n in self.sample_names:
            if 'ext' in n:
                tmp_sample_name = n.rsplit('-', 1)[0]
            else:
                tmp_sample_name = n
            
            if not tmp_sample_name in self.lumi_clusters.keys():
                self.lumi_clusters[tmp_sample_name] = [tmp_sample_name]
            else:
                self.lumi_clusters[tmp_sample_name].append(n)
        return self.lumi_clusters   

    def getPath(self, name):
        sample_infos = [line.split('%')[0].strip() for line in open(self.path)]                     # Strip % comments and \n charachters
        sample_infos = [line.split() for line in sample_infos if line]                              # Get lines into tuples
        for sample in sample_infos:
            if sample[0] == name: return sample[1]
        return None        


if __name__ == '__main__':
    sample_manager = SampleManager(2016, 'noskim', 'test')

    s = sample_manager.getSample('ZZTo4L')
    print s.name, s.xsec
    s = sample_manager.getSample('TTJets-Dilep')
    print s.name, s.xsec
    s = sample_manager.getSample('ZZTo4L')
    print s.name, s.xsec
    print sample_manager.getSampleNames(BASE_PATH+'/Sublists/test.conf')
    print sample_manager.makeLumiClusters()