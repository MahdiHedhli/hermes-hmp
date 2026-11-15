"""Complete path-policy equivalence for the native-byte control scan."""
import pytest
from hmp_startup import gateway_approval  # complete the supported startup import cycle
from hmp_plugin import presentation_startup_artifacts as a


@pytest.mark.parametrize('point', (*range(32),127))
@pytest.mark.parametrize('position',(0,1,2))
def test_every_forbidden_control_is_rejected_at_each_path_position(point,position):
    path=('/'+chr(point)+'abc' if position==0 else
          '/ab'+chr(point)+'cd' if position==1 else '/abc'+chr(point))
    with pytest.raises(a.ArtifactObservationError):a._expected((a.ExpectedArtifact(path,0,'a'*64),))


_PATH_CASES=(
    ('/a',True),('',False),('/',False),('relative',False),('//a',False),('/a/',False),
    ('/a//b',False),('/a/./b',False),('/a/../b',False),('/a/.',False),('/a/..',False),
    ('/a.b',True),('/a b',True),('/a\\b',True),('/é/文件/😀',True),
    ('/x\u0080\u009f',True),('/x\u2028\u2029',True),('/x\ufeff\uffff\U0010ffff',True),
    ('/'+'a'*4095,True),('/'+'a'*4096,False),('/'+'é'*2047+'x',True),('/'+'é'*2048,False),
    ('/'+'/'.join(['a']*64),True),('/'+'/'.join(['a']*65),False),
)
@pytest.mark.parametrize('path,accepted',_PATH_CASES)
def test_absolute_path_unicode_byte_and_segment_boundaries(path,accepted):
    row=a.ExpectedArtifact(path,0,'a'*64)
    if accepted:assert a._expected((row,)) is None
    else:
        with pytest.raises(a.ArtifactObservationError):a._expected((row,))


@pytest.mark.parametrize('fault',('negative','size_bool','oversize','size_float',
    'digest_type','digest_short','digest_long','digest_upper','digest_nonhex',
    'duplicate','empty','rows_list','row_tuple'))
def test_other_generic_row_validation_remains_enforced(fault):
    row=a.ExpectedArtifact('/a',0,'a'*64);rows=(row,)
    if fault=='negative':rows=(row._replace(size=-1),)
    elif fault=='size_bool':rows=(row._replace(size=True),)
    elif fault=='oversize':rows=(row._replace(size=a._MAX_FILE+1),)
    elif fault=='size_float':rows=(row._replace(size=0.0),)
    elif fault=='digest_type':rows=(row._replace(sha256=b'a'*64),)
    elif fault=='digest_short':rows=(row._replace(sha256='a'*63),)
    elif fault=='digest_long':rows=(row._replace(sha256='a'*65),)
    elif fault=='digest_upper':rows=(row._replace(sha256='A'*64),)
    elif fault=='digest_nonhex':rows=(row._replace(sha256='g'*64),)
    elif fault=='duplicate':rows=(row,row)
    elif fault=='empty':rows=()
    elif fault=='rows_list':rows=[row]
    else:rows=(tuple(row),)
    with pytest.raises(a.ArtifactObservationError):a._expected(rows)


@pytest.mark.parametrize('fault',('rows','row','path','str_subclass','row_subclass','size','digest'))
def test_foreign_protocols_are_not_invoked_before_exact_type_refusal(fault):
    calls=[]
    class Foreign:
        def __getattribute__(self,name):calls.append('get');raise AssertionError('foreign get')
        def __len__(self):calls.append('len');raise AssertionError('foreign len')
        def __iter__(self):calls.append('iter');raise AssertionError('foreign iter')
        def __hash__(self):calls.append('hash');raise AssertionError('foreign hash')
        def __eq__(self,other):calls.append('eq');raise AssertionError('foreign eq')
    class Path(str):
        def encode(self,*args,**kwargs):calls.append('encode');raise AssertionError('foreign encode')
    class Row(a.ExpectedArtifact):
        def __getattribute__(self,name):calls.append('rowget');raise AssertionError('foreign rowget')
    row=a.ExpectedArtifact('/a',0,'a'*64)
    if fault=='rows':rows=Foreign()
    elif fault=='row':rows=(Foreign(),)
    elif fault=='path':rows=(row._replace(path=Foreign()),)
    elif fault=='str_subclass':rows=(row._replace(path=Path('/a')),)
    elif fault=='row_subclass':rows=(Row('/a',0,'a'*64),)
    elif fault=='size':rows=(row._replace(size=Foreign()),)
    else:rows=(row._replace(sha256=Foreign()),)
    with pytest.raises(a.ArtifactObservationError):a._expected(rows)
    assert calls==[]


def test_every_unicode_code_point_preserves_the_original_control_policy():
    # Full production validation, not a reimplementation of translate(). This
    # expected policy is independent of UTF-8 byte representation and literals.
    for point in range(0x110000):
        row=a.ExpectedArtifact('/x'+chr(point),0,'a'*64)
        if 0xd800<=point<=0xdfff:
            with pytest.raises(UnicodeEncodeError):a._expected((row,))
        elif point<32 or point in (127,ord('/')):
            with pytest.raises(a.ArtifactObservationError):a._expected((row,))
        else:assert a._expected((row,)) is None,hex(point)


def test_counts_sizes_and_aggregate_limits_are_unchanged():
    rows=tuple(a.ExpectedArtifact('/f'+str(i),0,'a'*64) for i in range(a._MAX_FILES))
    assert a._expected(rows) is None
    with pytest.raises(a.ArtifactObservationError):a._expected((*rows,a.ExpectedArtifact('/extra',0,'a'*64)))
    count=a._MAX_TOTAL//a._MAX_FILE
    assert count+1<=a._MAX_FILES and count*a._MAX_FILE==a._MAX_TOTAL
    rows=tuple(a.ExpectedArtifact('/s'+str(i),a._MAX_FILE,'a'*64) for i in range(count))
    assert a._expected(rows) is None
    with pytest.raises(a.ArtifactObservationError):a._expected((*rows,a.ExpectedArtifact('/over',1,'a'*64)))


def test_previous_success_does_not_authorize_a_later_changed_path():
    row=a.ExpectedArtifact('/safe',0,'a'*64)
    assert a._expected((row,)) is None
    with pytest.raises(a.ArtifactObservationError):a._expected((row._replace(path='/unsafe\x00'),))
