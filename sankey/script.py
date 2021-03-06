from optparse import OptionParser
import pandas as pd
import json


ontology_term = {}
ontology_gene = {}
node_index = {}

def read_gen_ontology():
    df = pd.read_csv(filepath_or_buffer="gen_ontology.csv")
    return df

def read_ft():
    ft = set([])
    with open("TFs.txt", "r") as f:
        for line in f.readlines():
            ft.add(line.strip("\n"))
    return ft

def read_ft_im():
    df = pd.read_csv(filepath_or_buffer="regulon_2WsC_cy40.sif", sep='\t')
    return df

def read_firma_molecular():
    df = pd.read_csv(filepath_or_buffer="ms_k_sorted.csv")
    return df

def read_genes_no_diferenciados():
    df = pd.read_csv(filepath_or_buffer="etc_k_sorted.csv")
    return df

def clean_nodes_links(nodes, links):
    indexes = set([link["source"] for link in links])
    indexes = indexes.union(set([link["target"] for link in links]))
    n_nodes = []
    n_links = []
    other_index = {}
    for n_index, index in enumerate(indexes):
        other_index[index] = n_index
        n_nodes.append(nodes[index])

    for values in links:
        r = {}
        try:
            s = {"source": other_index[values["source"]]}
        except KeyError:
            s = {"source": values["source"]}

        try:
            t = {"target": other_index[values["target"]]}
        except KeyError:
            s = {"target": values["target"]}

        r.update(s)
        r.update(t)
        r["value"] = values["value"]
        n_links.append(r)

    return n_nodes, n_links

def unique(data, f=lambda v:"{}{}".format(v["source"], v["target"])):
    from collections import OrderedDict
    unique_data = OrderedDict()
    for value in data:
        key = f(value)
        if not key in unique_data:
            unique_data[key] = {"source": value["source"], "target": value["target"], "value": value["value"]}
    return unique_data.values()

def join(left, right):
    from collections import defaultdict

    join_data = []
    right_values = {right_value["source"]: right_value for right_value in right}
    for left_value in left:
        try:
            right_value = right_values[left_value["source"]]
            join_data.append({
                "source": left_value["target"], 
                "target": right_value["target"], 
                "value": right_value["value"]})
        except KeyError:
            pass
            #join_data.append({
            #    "source": left_value["target"], 
            #    "target": node_index["UNKNOW"], 
            #    "value": left_value["value"]})
    return join_data

def get_linked(search_space, links, length=0, im=10):
    import networkx as nx
    G = nx.DiGraph()

    edges = [(link["source"], link["target"], link["value"]) for link in links]
    G.add_weighted_edges_from(edges)

    def only_paths_of_size(paths):
        return [edges for edges in paths if len(edges) >= length]

    uv_count = {}
    linked = []
    search_space_unique = unique(search_space, f=lambda v:"{}".format(v["source"]))
    for link in search_space_unique:
        shorted = nx.shortest_path(G, source=link["source"])
        paths = only_paths_of_size(list(shorted.values()))
        for edges in paths:
            vertices = list(zip(edges, edges[1:]))
            last_u, last_v = vertices[-1]
            if G[last_u][last_v]["weight"] >= im:
                for u, v in vertices:
                    key = "{}{}".format(u,v)
                    if not key in uv_count:
                        linked.append({
                            "source": u, 
                            "target": v, 
                            "value": None})
                        uv_count[key] = 0
                    uv_count[key] += 1

    for link in linked:
        u = link["source"]
        v = link["target"]
        key = "{}{}".format(u,v)
        link["value"] = uv_count.get(key, G[u][v]["weight"])
            
    return linked
        

def ontology_graph(name, search_space_ontology):
    data = []
    for gene, ontologies in sorted(search_space_ontology.items(), key=lambda x: x[0]):
        for key_ontology in ontologies[name]:
            term = ontology_term[key_ontology]
            data.append({"source": node_index[gene], "target": node_index[term], "value": 1})
    return data

def firma_molecular_graph(fm, gnd, ft_im):
    data = []
    fm_set = set(fm["name"])
    gnd_set = set(gnd["name"])
    for i, row in ft_im.iterrows():
        if row["blanco"] in fm_set:
            target = "Firma Molecular"
        elif row["blanco"] in gnd_set:
            target = "Genes no diferenciados"
        else:
            continue

        data.append({
            "source": node_index[row["ft"]], 
            "target": node_index[target], 
            "value": abs(row["im"])})
    return data

def run(options):
    df = read_gen_ontology()
    ft = read_ft()
    df = df.drop_duplicates(subset="genesym")
    fm = read_firma_molecular()
    gnd = read_genes_no_diferenciados()
    ft_im = read_ft_im()

    gene_ont = ["Gene Ontology Biological Process", "Gene Ontology Cellular Component", 
                "Gene Ontology Molecular Function"]
    gene_ont_abbrv = {"Gene Ontology Biological Process": "gbp", 
                        "Gene Ontology Cellular Component": "gcc", 
                        "Gene Ontology Molecular Function": "gmf"}
    df_ft = df[df["genesym"].isin(ft)]
    gene_ontology = {}
    ontologies = {}
    ontology_term_list = set([])
    columns = ["genesym"] + gene_ont
    for i, row in df_ft[columns].iterrows():
        for ontology in gene_ont:
            for go in row[ontology].split("///"):
                go_terms = go.split("//")
                if len(go_terms) >= 2:
                    go_id = go_terms.pop(0)
                    key = go_id.strip()
                    ontology_term.setdefault(key, [])
                    ontologies.setdefault(ontology, set([]))
                    ontology_gene.setdefault(key, [])
                    gene_ontology.setdefault(row["genesym"], dict(zip(gene_ont, [[], [], []])))
                    ontologies[ontology].add(key)
                    gene_ontology[row["genesym"]][ontology].append(key)
                    ontology_gene[key].append(row["genesym"])
                    term = go_terms[0].strip()
                    ontology_term[key] = gene_ont_abbrv[ontology]+":"+term               
                    ontology_term_list.add(gene_ont_abbrv[ontology]+":"+term)

    fm_gnd_set = set(list(fm["name"]) + list(gnd["name"]))
    gene_set = set(gene_ontology.keys())
    
    search_space_ontology = {}
    for gene in gene_set.intersection(fm_gnd_set):
        search_space_ontology[gene] = gene_ontology[gene]

    s_nodes = set([])
    nodes = sorted(list(s_nodes.union(set(["UNKNOW"]), ft, ontology_term_list, fm_gnd_set, set(["Firma Molecular", "Genes no diferenciados"]))))

    for i, term in enumerate(nodes):
        if not term in node_index:
            node_index[term] = i

    pipeline = []
    if options.cellular_component:
        pipeline.append(ontology_graph("Gene Ontology Cellular Component", search_space_ontology))
    if options.biological_process:
        pipeline.append(ontology_graph("Gene Ontology Biological Process", search_space_ontology))
    if options.molecular_function:
        pipeline.append(ontology_graph("Gene Ontology Molecular Function", search_space_ontology))
    
    pipeline.append(firma_molecular_graph(fm, gnd, ft_im))
    links = [v for v in pipeline[0]]
    for p1, p2 in zip(pipeline, pipeline[1:]):
        for v in join(p1, p2):
            links.append(v)

    paths = get_linked(pipeline[0], links, length=len(pipeline)+1, im=options.im)
    print("PATHS", len(paths))
    n_nodes, n_links = clean_nodes_links(nodes, paths)
    result = json_sankey(n_nodes, n_links, type_=options.type)

    with open("sankey.json", "w") as f:
        f.write(json.dumps(result))

def json_sankey(n_nodes, n_links, type_="normal"):
    if type_ == "normal":
        result = {"nodes": [{"name": node} for node in n_nodes], "links": n_links}
    elif type_ == "colors":
        result = {"nodes": [{"name": node, "id": node.lower().replace(" ", "_") + "_score"} for node in n_nodes],
                "links": n_links}
    return result

class Test(object):
    im = 10
    cellular_component = True
    biological_process = True
    type = "normal"

def test():
    options = Test()
    run(options)

if __name__ == '__main__':
    parser = OptionParser("%prog [options]")
    parser.add_option("-c", "--cellular_component", action="store_true", default=False)
    parser.add_option("-b", "--biological_process", action="store_true", default=False)
    parser.add_option("-m", "--molecular_function", action="store_true", default=False)
    parser.add_option("-i", "--im", action="store", default=0, type='float')
    parser.add_option("-t", "--type", action="store", default="normal", type='string')
    options, args = parser.parse_args()
    run(options)
