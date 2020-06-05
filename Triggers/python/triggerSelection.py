def applyCustomTriggers(triggers):
    if isinstance(triggers, (list,)):
        return any(triggers)
    else:
        return triggers

def applyTriggersPerCategory(chain, cat):
    triggers = returnCategoryTriggers(chain, cat)
    return applyCustomTriggers(triggers)

def listOfTriggersAN2017014(chain):
    list_of_triggers = []
    list_of_triggers.append(chain._passTrigger_eee)
    list_of_triggers.append(chain._passTrigger_eem)
    list_of_triggers.append(chain._passTrigger_emm)
    list_of_triggers.append(chain._passTrigger_mmm)
    list_of_triggers.append(chain._HLT_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL_DZ)
    list_of_triggers.append(chain._passTrigger_em)
    list_of_triggers.append(chain._passTrigger_mm)
    list_of_triggers.append(chain._HLT_Ele27_WPTight_Gsf)
    list_of_triggers.append(chain._HLT_IsoMu24)
    list_of_triggers.append(chain._HLT_IsoTkMu24)
    return list_of_triggers

def listOfTriggers2016(chain):
    list_of_triggers = []
    list_of_triggers.append(chain._HLT_DoubleMediumCombinedIsoPFTau35_Trk1_eta2p1_Reg)
    list_of_triggers.append(chain._passTrigger_mt)
    list_of_triggers.append(chain._passTrigger_et)
    list_of_triggers.append(chain._passTrigger_eee)
    list_of_triggers.append(chain._passTrigger_eem)
    list_of_triggers.append(chain._passTrigger_emm)
    list_of_triggers.append(chain._passTrigger_mmm)
    list_of_triggers.append(chain._HLT_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL_DZ)
    list_of_triggers.append(chain._passTrigger_em)
    list_of_triggers.append(chain._passTrigger_mm)
    list_of_triggers.append(chain._HLT_Ele27_WPTight_Gsf)
    list_of_triggers.append(chain._HLT_IsoMu24)
    list_of_triggers.append(chain._HLT_IsoTkMu24)
    return list_of_triggers

def passTriggers(chain, year, oldAN=False):
    if oldAN:
        return any(listOfTriggersAN2017014(chain))

    if year == 2016 and any(listOfTriggers2016(chain)): return True
    elif year == 2017 and any(listOfTriggers2017(chain)): return True
    elif year == 2018 and any(listOfTriggers2018(chain)): return True
    return False


    


