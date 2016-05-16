class EpigenomeStats:
    def __init__(self, wepigenomes):
        self.wepigenomes = wepigenomes

        mm10b = self.wepigenomes.GetByAssemblyAndAssays("mm10", "BothDNaseAndH3K4me3")
        mm10d = self.wepigenomes.GetByAssemblyAndAssays("mm10", "DNase")
        mm10h = self.wepigenomes.GetByAssemblyAndAssays("mm10", "H3K4me3")
        hg19b = self.wepigenomes.GetByAssemblyAndAssays("hg19", "BothDNaseAndH3K4me3")
        hg19d = self.wepigenomes.GetByAssemblyAndAssays("hg19", "DNase")
        hg19h = self.wepigenomes.GetByAssemblyAndAssays("hg19", "H3K4me3")

        self.mouse_both = len(mm10b)
        self.human_both = len(hg19b)

        self.mouse_not_both = len(set([x.web_id() for x in mm10h.epis] +
                                      [x.web_id() for x in mm10h.epis]) -
                                  set([x.web_id() for x in mm10b.epis]))

        self.human_not_both = len(set([x.web_id() for x in hg19d.epis] +
                                      [x.web_id() for x in hg19h.epis]) -
                                  set([x.web_id() for x in hg19b.epis]))
