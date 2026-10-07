import {afterEach,expect,it,vi} from 'vitest';
import {render,screen,fireEvent,waitFor,cleanup} from '@testing-library/react';
import axe from 'axe-core';
import App from './App';
vi.mock('./bridge',()=>({native:false,inspect:async()=>({code:0,success:true,lines:['SKYVIEW_EVENT|validation|PASS|Git: 2.49','SKYVIEW_EVENT|summary|0|Done'],log_path:'Preview',platform:{label:'Windows 11 x64',supported:true}}),operate:async()=>({code:1,success:false,lines:['SKYVIEW_EVENT|error|test|A test package failed','SKYVIEW_EVENT|summary|1|Failed'],log_path:'test.log',platform:{label:'Windows 11',supported:true}}),open:async()=>{}}));
afterEach(cleanup);
it('shows a keyboard-accessible UI with no detected axe violations',async()=>{const {container}=render(<App/>);await screen.findByRole('heading',{name:'Ready',exact:true});const results=await axe.run(container,{rules:{'color-contrast':{enabled:false}}});expect(results.violations).toEqual([]);expect(screen.getByRole('button',{name:'Install Development Environment'})).toBeTruthy();});
it('shows graphical validation and labels optional statuses',async()=>{render(<App/>);await screen.findByRole('heading',{name:'Ready',exact:true});fireEvent.click(screen.getByRole('button',{name:'Validation'}));expect(screen.getByRole('table')).toBeTruthy();expect(screen.getByText('PASS')).toBeTruthy();});
it('offers a retry and focuses the result after a child failure',async()=>{render(<App/>);await screen.findByRole('heading',{name:'Ready',exact:true});fireEvent.click(screen.getByRole('button',{name:'Install Development Environment'}));await screen.findByText('A test package failed');expect(screen.getByRole('button',{name:'Retry install'})).toBeTruthy();await waitFor(()=>expect(document.activeElement?.textContent).toBe('Your environment needs attention.'));});

