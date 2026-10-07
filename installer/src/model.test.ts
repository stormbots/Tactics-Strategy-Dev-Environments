import {describe,it,expect} from 'vitest';
import {initialState,reducer,parseEvent,environmentStatus,checksFrom,type Mode,type Report} from './model';
const report=(lines:string[],code=0):Report=>({lines,code,success:code===0,log_path:'example.log',platform:{label:'Windows 11',supported:true}});
const valid=['SKYVIEW_EVENT|validation|PASS|Git: 2.49','SKYVIEW_EVENT|validation|INFO|Git identity: not configured','SKYVIEW_EVENT|summary|0|Done'];
describe('structured protocol',()=>{
  it('parses events and preserves message pipes',()=>expect(parseEvent('SKYVIEW_EVENT|progress|45|Installing | editor')?.message).toBe('Installing | editor'));
  it('rejects malformed events and arbitrary native output',()=>{for(const line of ['SKYVIEW_EVENT|progress|101|Bad','SKYVIEW_EVENT|progress|-1|Bad','SKYVIEW_EVENT|validation|OK|Bad','SKYVIEW_EVENT|summary|no|Bad','Node installed','SKYVIEW_EVENT|unknown|x|y'])expect(parseEvent(line)).toBeNull();});
  it('parses all validation severities',()=>expect(checksFrom(['PASS','WARNING','FAIL','INFO'].map(s=>`SKYVIEW_EVENT|validation|${s}|Check`)).map(c=>c.status)).toEqual(['PASS','WARNING','FAIL','INFO']));
});
describe('operation states',()=>{
  for(const mode of ['install','repair','validate','update'] as Mode[])it(`completes ${mode} only with successful validation`,()=>{let state=reducer(initialState,{type:'start',mode});expect(state.stage).toBe('running');expect(state.mode).toBe(mode);state=reducer(state,{type:'line',line:'SKYVIEW_EVENT|progress|45|Working'});expect(state.progress).toBe(45);state=reducer(state,{type:'complete',report:report(valid)});expect(state.stage).toBe('success');expect(state.progress).toBe(100);});
  it('treats child exit failures as failures',()=>expect(reducer(initialState,{type:'complete',report:report(valid,5)}).stage).toBe('failure'));
  it('requires a complete validator report',()=>expect(reducer(initialState,{type:'complete',report:report([])}).stage).toBe('failure'));
  it('fails even if a contradictory summary claims success',()=>expect(reducer(initialState,{type:'complete',report:report([...valid,'SKYVIEW_EVENT|validation|FAIL|Node'])}).stage).toBe('failure'));
  it('preserves meaningful backend errors',()=>expect(reducer(initialState,{type:'complete',report:report(['SKYVIEW_EVENT|error|pycharm|Checksum verification failed'],1)}).error).toBe('Checksum verification failed'));
  it('allows retry without stale errors or validation',()=>{const s=reducer({...initialState,stage:'failure',error:'old',checks:[{status:'FAIL',message:'Old'}]},{type:'start',mode:'repair'});expect(s.error).toBe('');expect(s.checks).toEqual([]);});
  it('keeps progress monotonic',()=>{const s=reducer({...initialState,progress:60},{type:'line',line:'SKYVIEW_EVENT|progress|30|Phase'});expect(s.progress).toBe(60);});
});
describe('workstation state detection',()=>{
  it('handles all five required states',()=>{
    expect(environmentStatus([{status:'FAIL',message:'Git: not installed'}])).toBe('Not installed');
    expect(environmentStatus([{status:'PASS',message:'Git: 2.x'},{status:'FAIL',message:'Node.js: not installed'}])).toBe('Partially installed');
    expect(environmentStatus([{status:'PASS',message:'Git: 2.x'},{status:'FAIL',message:'Weekly maintenance'}])).toBe('Needs repair');
    expect(environmentStatus(checksFrom(valid))).toBe('Ready');
    expect(environmentStatus(checksFrom(valid),true)).toBe('Needs update');
  });
  it('does not fail optional identity or authentication',()=>expect(environmentStatus(checksFrom(valid))).toBe('Ready'));
});
