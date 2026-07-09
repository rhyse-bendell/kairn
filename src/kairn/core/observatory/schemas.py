from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any

class _ILoc:
    def __init__(self, rows): self.rows=rows
    def __getitem__(self, i): return self.rows[i]
class SimpleDataFrame:
    def __init__(self, rows, columns=None): self.rows=rows; self.columns=columns or [] ; self.iloc=_ILoc(rows)
    def to_csv(self, path, index=False):
        import csv
        with open(path,'w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f, fieldnames=self.columns, extrasaction='ignore'); w.writeheader(); w.writerows(self.rows)

@dataclass
class ObservatoryTable:
    table_id: str; title: str; description: str; source_stream: str; scope: dict; columns: list[str]; rows: list[dict]; caveat: str|None=None
    def to_dict(self): return asdict(self)
@dataclass
class ObservatoryChartSpec:
    chart_id: str; title: str; description: str; chart_type: str; table_id: str; x: str|None; y: str|None; group: str|None; path: str|None=None; caveat: str|None=None
    def to_dict(self): return asdict(self)
@dataclass
class ObservatoryReport:
    project_id: str|None; project_name: str|None; project_root: str|None; run_id: str|None; created_at: str; scope: dict; tables: list[ObservatoryTable]; charts: list[ObservatoryChartSpec]; snippets: list[dict]; warnings: list[str]; caveats: list[str]
    def to_dict(self): return asdict(self)

def table_to_dataframe(table): return SimpleDataFrame(table.rows, table.columns)
def table_from_rows(table_id,title,description,source_stream,rows=None,scope=None,columns=None,caveat=None):
    rows=rows or []
    if columns is None:
        columns=[]
        for r in rows:
            for k in r:
                if k not in columns: columns.append(k)
    return ObservatoryTable(table_id,title,description,source_stream,scope or {},columns,rows,caveat)
def report_summary(report): return {'project_id':report.project_id,'project_name':report.project_name,'table_count':len(report.tables),'chart_count':len(report.charts),'snippet_count':len(report.snippets),'warning_count':len(report.warnings),'caveat_count':len(report.caveats),'tables':[t.table_id for t in report.tables]}
