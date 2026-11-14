"""Synthetic child-only fault timing; never a production callback or guard bypass."""
TRACE_HELPERS = r'''
_synthetic_trace_routes={}
_synthetic_native_routes=[]
def synthetic_profile(frame,event,arg):
    if event=='c_call':
        for native,code,callback in _synthetic_native_routes:
            if arg is native and frame.f_code is code:callback(frame)
def observe_synthetic_native(native,code,callback):
    assert sys.getprofile() in (None,synthetic_profile)
    _synthetic_native_routes.append((native,code,callback))
    sys.setprofile(synthetic_profile)
def synthetic_line(code,fragment):
    lines=Path(code.co_filename).read_text().splitlines()
    end=max(line for _,_,line in code.co_lines() if line is not None)
    matches=[i+1 for i in range(code.co_firstlineno-1,end) if fragment in lines[i]]
    assert len(matches)==1,(code.co_name,fragment,matches)
    return matches[0]
def synthetic_trace(frame,event,arg):
    route=_synthetic_trace_routes.get(frame.f_code)
    if route is None:return None
    if event=='line':
        callback=route.get(frame.f_lineno)
        if callback is not None:callback(frame)
    return synthetic_trace
def trace_synthetic_boundary(code,fragment,callback):
    assert sys.gettrace() in (None,synthetic_trace)
    _synthetic_trace_routes.setdefault(code,{})[synthetic_line(code,fragment)]=callback
    sys.settrace(synthetic_trace)
'''
