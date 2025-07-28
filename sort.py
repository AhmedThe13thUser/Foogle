top1000sites = {}
nosites = {}

with open("top1000sites", "r") as f:
    top1000sites = {line.strip() for line in f.readlines()}


with open("known_no.txt", "r") as f:
    nosites = {line.strip() for line in f.readlines()}


def set_nand(set_a, set_b, universal_set=None):
    if universal_set is None:
        universal_set = set_a.union(set_b)
    return universal_set.difference(set_a.intersection(set_b))


with open("starting_urls.txt", "w") as f:
    for site in set_nand(top1000sites, nosites, universal_set=top1000sites):
        f.write(f"{site}\n")
