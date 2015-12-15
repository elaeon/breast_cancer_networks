from optparse import OptionParser
import pandas as pd

def firma_molecular_graph(fm):
    data = []
    for i, row in fm.iterrows():
        data.append({
            "source": row["fm"], 
            "target": row["fm_gene"], 
            "value": 1})
    return data

def signature_graph(genes):
    data = []
    for i, row in genes.iterrows():
        data.append({
            "source": row["gene"], 
            "target": str(abs(row["value"])), 
            "value": 1})
    return data

def run():
    from sankey import Sankey

    df = pd.read_csv(filepath_or_buffer="rdb_sankeys/lumb_rdb_regulon.sif", sep='\t')
    df_genes = pd.read_csv(filepath_or_buffer="rdb_sankeys/lumb_rdb_signature.txt", sep='\t')
    base = df[df["fm"].isin(df["fm_gene"])]

    universe1 = set((r["fm"] for i, r in base.iterrows()))
    universe2 = set(r["gene"] for i, r in df_genes.iterrows())
    universe3 = set(str(abs(r["value"])) for i, r in df_genes.iterrows())
    universe1_1 = set((r["fm_gene"] for i, r in base.iterrows()))

    sankey = Sankey()
    sankey.add_universe(universe1)
    sankey.add_universe(universe2)
    sankey.add_universe(universe3)
    sankey.add_universe(universe1_1)

    sankey.add_pipeline(firma_molecular_graph(base))
    sankey.add_pipeline(signature_graph(df_genes))
    
    last = set([sankey.universe_index[e] for e in universe3])
    def only_paths_of_size(paths, length=3):
        return [edges for edges in paths if edges[-1] in last and len(edges) == length]

    paths = sankey.paths(base["fm"], only_paths_of_size)
    sankey.json(paths, name="sankey2.json")

if __name__ == '__main__':
    run()
