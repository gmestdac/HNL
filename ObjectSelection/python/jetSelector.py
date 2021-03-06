from HNL.Tools.helpers import deltaR
from HNL.ObjectSelection.leptonSelector import isLooseLepton, isTightLepton

default_jet_selection = 'cut-based'

#
#       Defines jet WP and b-tagging
#
def isCleanFromLeptons(chain, index):
    for l in xrange(chain._nL):
        if not isTightLepton(chain, l): continue
        if deltaR(chain._lEta[l], chain._jetEta[index], chain._lPhi[l], chain._jetPhi[index]) < 0.4: return False
    return True

def isGoodJetAN2017014(chain, index, cleaned = True):
    if chain._jetPt[index] < 25:        return False
    if abs(chain._jetEta[index]) > 2.4: return False
    if not chain._jetIsLoose[index]:    return False
    if cleaned and not isCleanFromLeptons(chain, index):       return False
    return True

def isGoodJetCutBased(chain, index, cleaned = True):
    if chain._jetPt[index] < 25:        return False
    if abs(chain._jetEta[index]) > 2.4: return False
    if not chain._jetIsTight[index]:    return False
    if cleaned and not isCleanFromLeptons(chain, index):       return False
    return True

from bTagWP import getBTagWP, readBTagValue
def isBJet(chain, index, algo, wp, cleaned = True, selection = None):
    if selection is None:
        if not isGoodJet(chain, index, cleaned = cleaned, selection = default_jet_selection): return False
    else:
        if not isGoodJet(chain, index, cleaned = cleaned, selection = selection): return False
        
    if readBTagValue(chain, index, algo) < getBTagWP(chain.year, wp, algo): return False
    return True
    
def isGoodJet(chain, index, cleaned = True, selection = default_jet_selection):
    if selection == 'cut-based':
        return isGoodJetCutBased(chain, index, cleaned = cleaned)
    elif selection == 'AN2017014':
        return isGoodJetAN2017014(chain, index, cleaned = cleaned)
    else:
        return True
    
