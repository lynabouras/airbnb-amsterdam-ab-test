import pandas as pd
import numpy as np
import duckdb
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler


GROUP_COLORS = {"Groupe A": "#B06470", "Groupe B": "#EFD705"}

def load_and_clean():
    df = pd.read_csv("listings.csv") 
    df["price"] = df["price"].str.replace(r"[\$,]", "", regex=True).astype(float)

    for col in ["instant_bookable", "host_is_superhost"]:
        
        df[col] = df[col].map({"t": True, "f": False}) 
    
    for col in [
        "estimated_occupancy_l365d",
        "estimated_revenue_l365d",
        "number_of_reviews_ltm",
        "reviews_per_month",
    ]:
 
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0) 
  
    df["group"] = df["instant_bookable"].map(
        {True: "Groupe A", False: "Groupe B"} 
    )

    return df


def run_sql(df):
    con = duckdb.connect() 
    con.register("listings", df)
    out = {}
  
    out["summary"] = con.execute("""
        SELECT
            "group",
            COUNT(*) AS n,
            ROUND(AVG(number_of_reviews_ltm), 2)      AS avg_reviews, 
            ROUND(MEDIAN(number_of_reviews_ltm), 2)   AS med_reviews,
            ROUND(AVG(estimated_occupancy_l365d), 1)  AS avg_occupancy,
            ROUND(AVG(estimated_revenue_l365d))        AS avg_revenue,
            ROUND(MEDIAN(estimated_revenue_l365d))     AS med_revenue,
            ROUND(AVG(price), 2)                       AS avg_price,
            ROUND(
                100.0 * SUM(CASE WHEN host_is_superhost THEN 1 ELSE 0 END)
                / COUNT(*), 1
            )                                          AS pct_superhost
        FROM listings
        GROUP BY "group"
        ORDER BY "group"
    """).df()

    out["by_neighbourhood"] = con.execute("""
        SELECT
            neighbourhood_cleansed AS neighbourhood,
            "group",
            COUNT(*)                               AS n,
            ROUND(AVG(number_of_reviews_ltm), 2)  AS avg_reviews,
            ROUND(AVG(estimated_revenue_l365d))    AS avg_revenue
        FROM listings
        GROUP BY neighbourhood_cleansed, "group"
        HAVING COUNT(*) >= 5
        ORDER BY neighbourhood_cleansed, "group"
    """).df()
    out["by_room_type"] = con.execute("""
        SELECT
            room_type,
            "group",
            COUNT(*)                               AS n,
            ROUND(AVG(number_of_reviews_ltm), 2)  AS avg_reviews,
            ROUND(AVG(price), 2)                   AS avg_price
        FROM listings
        GROUP BY room_type, "group"
        ORDER BY room_type, "group"
    """).df()

    out["reviews_buckets"] = con.execute("""
        SELECT
            "group",
            CASE
                WHEN number_of_reviews_ltm = 0   THEN '0'
                WHEN number_of_reviews_ltm <= 5  THEN '1–5'
                WHEN number_of_reviews_ltm <= 20 THEN '6–20'
                WHEN number_of_reviews_ltm <= 50 THEN '21–50'
                ELSE '50+'
            END AS bucket,
            COUNT(*) AS n
        FROM listings
        GROUP BY "group", bucket
        ORDER BY "group", bucket
    """).df()
 
    out["top_revenue_neigh"] = con.execute("""
        SELECT
            neighbourhood_cleansed AS neighbourhood,
            "group",
            ROUND(AVG(estimated_revenue_l365d)) AS avg_revenue,
            COUNT(*) AS n
        FROM listings
        GROUP BY neighbourhood_cleansed, "group"
        HAVING COUNT(*) >= 10
        ORDER BY avg_revenue DESC
        LIMIT 30
    """).df()

    con.close()
    return out


def run_stats(df):
    a = df[df["group"] == "Groupe A"] 
    b = df[df["group"] == "Groupe B"]
    #les metriques que l'on compare entre les deux groupes 
    metrics = [
        ("number_of_reviews_ltm",       "Avis (12 mois)"),
        ("estimated_occupancy_l365d",   "Occupation (jours/an)"),
        ("estimated_revenue_l365d",     "Revenu estimé (€/an)"),
    ]

    out = {}
    for col, label in metrics:
        u, p = stats.mannwhitneyu(a[col].values, b[col].values, alternative="two-sided")
        n1, n2 = len(a), len(b)
        r = 1 - (2 * u) / (n1 * n2)
     
        ar = abs(r)
        if ar < 0.1:
            effect_label = "Négligeable"
        elif ar < 0.3:
            effect_label = "Faible"
        elif ar < 0.5:
            effect_label = "Modéré"
        else:
            effect_label = "Fort"

        out[col] = {
            "label":        label,
            "p_value":      float(p),
            "u_stat":       float(u),
            "effect_r":     float(r),
            "effect_label": effect_label,
            "mean_a":       float(a[col].mean()),
            "mean_b":       float(b[col].mean()),
            "median_a":     float(a[col].median()),
            "median_b":     float(b[col].median()),
            "n_a":          n1,
            "n_b":          n2,
            "significant":  bool(p < 0.05), 
        }

    return out


def apply_psm(df):
   
    df_clean = df.dropna(subset=["price", "host_is_superhost"]).copy()

    features = pd.get_dummies(
        df_clean[["price", "reviews_per_month", "host_is_superhost", "room_type", "neighbourhood_cleansed"]],
        drop_first=True
    )

    scaler = StandardScaler()
    X = scaler.fit_transform(features)
    y = (df_clean["group"] == "Groupe A").astype(int)

    lr = LogisticRegression(max_iter=1000)
    lr.fit(X, y)
    df_clean["pscore"] = lr.predict_proba(X)[:, 1]

    a = df_clean[df_clean["group"] == "Groupe A"].copy()
    b = df_clean[df_clean["group"] == "Groupe B"].copy()

    nn = NearestNeighbors(n_neighbors=1)
    nn.fit(b[["pscore"]])
    distances, indices = nn.kneighbors(a[["pscore"]])

    caliper = 0.05 * df_clean["pscore"].std()

    matched_a_idx, matched_b_idx, used_b = [], [], set()

    
    pairs = sorted(zip(range(len(a)), distances[:, 0], indices[:, 0]), key=lambda x: x[1])

    for a_pos, dist, b_pos in pairs:
        if dist <= caliper and b_pos not in used_b:
            matched_a_idx.append(a_pos)
            matched_b_idx.append(b_pos)
            used_b.add(b_pos)

    matched = pd.concat([a.iloc[matched_a_idx], b.iloc[matched_b_idx]])
    return matched.drop(columns=["pscore"])


def run_pipeline():
    df = load_and_clean()
    sql = run_sql(df)
    stat_results = run_stats(df)
    return df, sql, stat_results


if __name__ == "__main__":
    df, sql, stat_results = run_pipeline()
    cols = ["estimated_occupancy_l365d",
        "estimated_revenue_l365d",
        "number_of_reviews_ltm",
        "reviews_per_month"]
    print(df[cols].dtypes) #etre sur 
    print("=" * 60)
    print("GROUP SUMMARY (SQL / DuckDB)")
    print("=" * 60)
    print(sql["summary"].to_string(index=False))

    print("\n" + "=" * 60)
    print("STATISTICAL TESTS (Mann-Whitney U, α = 0.05)")
    print("=" * 60)
    for col, res in stat_results.items():
        verdict = "SIGNIFICATIF" if res["significant"] else "non significatif"
        print(f"\n{res['label']}")
        print(f"  p-value      : {res['p_value']:.6f}  {verdict}")
        print(f"  Effect size r: {res['effect_r']:.4f}  ({res['effect_label']})")
        print(f"  Moy. A={res['mean_a']:.2f}  Moy. B={res['mean_b']:.2f}  "
              f"({(res['mean_a']-res['mean_b'])/res['mean_b']*100:+.1f}%)") #la moyenne d'augmentation du groupe A par rapport au B 


