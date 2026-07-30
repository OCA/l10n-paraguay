Manufacturing (MRP) integration for Paraguay's Maquila regime (Ley 7547/2025):

- **BOM INTN coefficients**: gross quantity (requirement factor), net quantity
  and loss percentage, plus the origin type of each component (temporary
  admission, national, Mercosur, imported). The net-quantity fields are derived
  from GRAP's `mrp_bom_line_net_qty`.
- **Maquila program** on manufacturing orders (computed from the BOM) with BOM,
  production and waste counters.
- **Waste management** (scrap, byproduct, defective) with destruction /
  nationalization / re-export destinations; destruction drafts a stock scrap.
- **VAN wizard**: national added value for a period, computed from the program's
  analytic cost minus foreign-origin inputs; it requires completed production
  to determine the origin split.
