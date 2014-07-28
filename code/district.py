#!/usr/bin/env python2.7 -B
"""compute district similarity for all schools in US"""

import pandas as pd
import numpy as np
import pdb

import similarity
import get_donorschoose
import get_nces
import get_census
import geojson
import subprocess


def bash(command):
    """bash wrapper for running topojson"""
    print "$ " + command
    p = subprocess.Popen(command.split(), stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    output, errors = p.communicate()
    if output:
        print output
    if errors:
        print errors


def district_similarity():
    """Compute district similarity matrix using census, NCES, and census district data.

    OUTPUT: Similarity object
            pickled Similarity object (optional)
    """

    census = get_census.all_states()

    columns = ["STNAME", "LATCOD", "LONCOD", "TOTALREV", "TFEDREV", "TSTREV", "TLOCREV", "TOTALEXP", "TCURSSVC", "TCAPOUT", "HR1", "HE1", "HE2"]
    nces = get_nces.districts(columns=columns, nonneg=True)

    ddf = pd.concat([census, nces.loc[census.index]], axis=1)

    sim = similarity.Similarity(ddf, ref_columns=["District Name", "State", "STNAME", "LATCOD", "LONCOD"])

    return sim


def potential_districts(sim):
    """Find potentially active districts outside of DonorsChoose network.

    OUTPUT: topojson with recommended school districts 
    """

    dc_districts = get_donorschoose.districts()

    all_dc = dc_districts.index
    most_active = set(dc_districts[dc_districts.activity > 3].index.values.astype(np.int))

    all_districts = set(sim.data.index.values.astype(np.int))
    potential = all_districts - (most_active & all_districts)

    rms = sim.rms_score(potential, most_active)
    norm_rms = (100*rms/rms.max()).astype(np.int)
      
    # list of sorted potential districts
    p = sorted(zip(potential, norm_rms), key=lambda (x, y): y, reverse=True)
    pdf = pd.DataFrame(p)
    pdf.columns = ["leaid", "score"]
    pdf.index = pdf.pop("leaid")
    recommend = pdf.index[:550]

    # 10 simliar active DonorsChoose schools revieved $x in donations with an average of y projects
    # take 10 schools for each state 

    rec = sim.data[["District Name", "STNAME", "LATCOD", "LONCOD"]].loc[recommend]
    lenrec = len(rec)
    rec.dropna(inplace=True)
    print "NaNs: dropped {} districts".format(lenrec - len(rec))

    features = []
    for leaid in rec.index.values:
        point = geojson.Point((rec["LONCOD"].loc[leaid], rec["LATCOD"].loc[leaid]))
        properties = {"name" : rec["District Name"].loc[leaid], 
                      "state": rec["STNAME"].loc[leaid],
                      "leaid": leaid,
                      "score": pdf.score.loc[leaid],
                      }
        features.append(geojson.Feature(geometry=point, properties=properties))

    collection = geojson.FeatureCollection(features) 

    basename = "districts"
    with open(basename+".json", "w") as geo:
        geo.write(geojson.dumps(collection))

    bash("topojson -p -o {}.topo.json {}.json".format(basename, basename))
#     bash("mv {}.json ../interactive/json/{}.json".format(basename))
#     bash("mv {}.topo.json ../interactive/json/{}.topo.json".format(basename))

    return rec
       

if __name__ == "__main__":
    sim = district_similarity()
    rec = potential_districts(sim)
