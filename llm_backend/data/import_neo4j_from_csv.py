"""
将 graphrag_2.1.0 预处理的 neo4j_data CSV 导入本地 Neo4j。
"""
import sys
import os
import re
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from neo4j import GraphDatabase
from app.core.config import settings

NEO4J_DATA = r"E:\develop\smart-customer\graphrag_2.1.0\graphrag\origin_data\data\neo4j_data"

URI = settings.NEO4J_URL
USER = settings.NEO4J_USERNAME
PASSWORD = settings.NEO4J_PASSWORD
DATABASE = settings.NEO4J_DATABASE

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

# label -> id_property_name 映射，边导入时需要
label_id_map = {}


def parse_col(col: str):
    """返回 (role, label, clean_name)"""
    m = re.search(r":(ID|LABEL|START_ID|END_ID|TYPE)(?:\((\w+)\))?$", col)
    if m:
        role = m.group(1)
        label = m.group(2)
        clean = col[: m.start()] if m.start() > 0 else col
        return (role, label, clean)
    return (None, None, col)


def import_nodes():
    files = sorted(f for f in os.listdir(NEO4J_DATA) if f.endswith("_nodes.csv"))
    total = 0
    for fname in files:
        fpath = os.path.join(NEO4J_DATA, fname)
        df = pd.read_csv(fpath)

        id_col = None
        label_val = None
        prop_map = []
        for c in df.columns:
            role, lbl, clean = parse_col(c)
            if role == "ID":
                id_col = (c, lbl, clean)
                prop_map.append((c, clean))
            elif role == "LABEL":
                val = df[c].iloc[0]
                label_val = val if pd.notna(val) else lbl
            elif role is None:
                prop_map.append((c, clean))

        if id_col is None:
            print(f"  SKIP {fname}: no :ID column")
            continue
        if label_val is None:
            label_val = id_col[1]

        # 记录此 label 的 ID 属性名
        label_id_map[label_val] = id_col[2]  # clean property name
        print(f"  Label '{label_val}' -> ID prop '{id_col[2]}'")

        count = 0
        with driver.session(database=DATABASE) as session:
            for _, row in df.iterrows():
                props = {}
                for raw_n, clean_n in prop_map:
                    v = row[raw_n]
                    if pd.notna(v):
                        if hasattr(v, "item"):
                            v = v.item()
                        if isinstance(v, pd.Timestamp):
                            v = str(v)
                        props[clean_n] = v

                prop_str = ", ".join(f"`{k}`: ${k}" for k in props)
                try:
                    session.run(f"CREATE (n:{label_val} {{{prop_str}}})", **props)
                    count += 1
                except Exception as e:
                    print(f"    ERROR: {e}")

        total += count
        print(f"  {fname}: {count} nodes")

    print(f"Total nodes: {total}")


def import_edges():
    files = sorted(f for f in os.listdir(NEO4J_DATA) if f.endswith("_edges.csv"))
    total = 0
    for fname in files:
        fpath = os.path.join(NEO4J_DATA, fname)
        df = pd.read_csv(fpath)

        s_raw = s_label = s_clean = None
        e_raw = e_label = e_clean = None
        t_raw = t_lbl = t_clean = None
        prop_map = []

        for c in df.columns:
            role, lbl, clean = parse_col(c)
            if role == "START_ID":
                s_raw, s_label = c, lbl
                # 查找此 label 的 ID 属性名
                s_clean = label_id_map.get(lbl, clean)
                if s_clean and s_clean.startswith(":"):
                    s_clean = label_id_map.get(lbl, "id")
            elif role == "END_ID":
                e_raw, e_label = c, lbl
                e_clean = label_id_map.get(lbl, clean)
                if e_clean and e_clean.startswith(":"):
                    e_clean = label_id_map.get(lbl, "id")
            elif role == "TYPE":
                t_raw, t_lbl, t_clean = c, lbl, clean
            elif role is None:
                prop_map.append((c, clean))

        if not s_raw or not e_raw:
            print(f"  SKIP {fname}: missing START_ID or END_ID")
            continue
        if not s_clean or not e_clean:
            print(f"  SKIP {fname}: no ID mapping for {s_label} or {e_label}")
            continue

        count = 0
        errors = 0
        with driver.session(database=DATABASE) as session:
            for _, row in df.iterrows():
                sid = row[s_raw]
                eid = row[e_raw]
                if pd.isna(sid) or pd.isna(eid):
                    continue

                # 关系类型
                rel_type = "RELATED_TO"
                if t_raw:
                    v = row[t_raw]
                    if pd.notna(v):
                        rel_type = str(v)
                    elif t_lbl:
                        rel_type = t_lbl

                # 边属性
                eprops = {}
                for raw_n, clean_n in prop_map:
                    v = row[raw_n]
                    if pd.notna(v):
                        if hasattr(v, "item"):
                            v = v.item()
                        if isinstance(v, pd.Timestamp):
                            v = str(v)
                        eprops[clean_n] = v

                params = {"sid": sid, "eid": eid, **eprops}
                eprop_str = ", ".join(f"`{k}`: ${k}" for k in eprops) if eprops else ""

                if eprop_str:
                    query = (
                        f"MATCH (a:{s_label} {{{s_clean}: $sid}}) "
                        f"MATCH (b:{e_label} {{{e_clean}: $eid}}) "
                        f"CREATE (a)-[r:{rel_type} {{{eprop_str}}}]->(b)"
                    )
                else:
                    query = (
                        f"MATCH (a:{s_label} {{{s_clean}: $sid}}) "
                        f"MATCH (b:{e_label} {{{e_clean}: $eid}}) "
                        f"CREATE (a)-[r:{rel_type}]->(b)"
                    )

                try:
                    session.run(query, **params)
                    count += 1
                except Exception as e:
                    errors += 1
                    if errors == 1:
                        print(f"    First error: {type(e).__name__}: {e}")
                        print(f"    Query: {query[:200]}")

        total += count
        status = f"({errors} errors)" if errors else ""
        print(f"  {fname}: {count} edges [{s_label}]-[{rel_type}]->[{e_label}] {status}")

    print(f"Total edges: {total}")


def main():
    print("=== Scanning node labels ===")
    # 先扫描节点文件建立 label->id 映射
    for fname in sorted(f for f in os.listdir(NEO4J_DATA) if f.endswith("_nodes.csv")):
        fpath = os.path.join(NEO4J_DATA, fname)
        df = pd.read_csv(fpath, nrows=1)
        for c in df.columns:
            role, lbl, clean = parse_col(c)
            if role == "ID":
                label_val = lbl
                # 也检查 LABEL 列
                for c2 in df.columns:
                    r2, l2, cl2 = parse_col(c2)
                    if r2 == "LABEL":
                        v = df[c2].iloc[0]
                        if pd.notna(v):
                            label_val = str(v)
                label_id_map[label_val] = clean
                print(f"  {label_val} -> {clean}")
                break

    print("\n=== Importing nodes ===")
    import_nodes()

    print("\n=== Importing edges ===")
    import_edges()

    with driver.session(database=DATABASE) as session:
        r = session.run("MATCH (n) RETURN count(n) AS total")
        nc = r.single()["total"]
        r = session.run("MATCH ()-[r]->() RETURN count(r) AS total")
        rc = r.single()["total"]
        print(f"\n=== RESULT: {nc} nodes, {rc} relationships ===")
        r = session.run("MATCH (n) RETURN DISTINCT labels(n) AS lbl, count(n) AS cnt ORDER BY cnt DESC")
        for rec in r:
            print(f"  {rec['lbl']}: {rec['cnt']}")

    driver.close()
    print("\n=== DONE ===")


if __name__ == "__main__":
    main()
