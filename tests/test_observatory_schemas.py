from kairn.core.observatory.schemas import *
def test_schema_summary():
    t=table_from_rows('x','X','d','s',[{'a':1}]); assert table_to_dataframe(t).iloc[0]['a']==1
    r=ObservatoryReport('p','n','r',None,'now',{},[t],[],[],[],[]); assert report_summary(r)['table_count']==1
