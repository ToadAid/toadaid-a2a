import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen} from '@testing-library/react';
import {useEffect} from 'react';
import {ThemeProvider, useTheme} from '../theme/ThemeContext';

type Observation = {state:string; applied:string|null};
function Probe({observations}:{observations:Observation[]}) {
 const {theme,toggleTheme}=useTheme();
 useEffect(() => {
  observations.push({state:theme,applied:document.documentElement.getAttribute('data-theme')});
 },[theme,observations]);
 return <button onClick={toggleTheme}>Switch theme</button>;
}
beforeEach(() => {
 localStorage.clear();
 document.documentElement.removeAttribute('data-theme');
});
afterEach(() => {
 cleanup();
 vi.restoreAllMocks();
 localStorage.clear();
 document.documentElement.removeAttribute('data-theme');
});

describe('theme is applied before descendant passive work',() => {
 it('applies URL dark preference before descendants even when saved preference is light',() => {
  localStorage.setItem('toadaid_theme','light');
  window.history.replaceState({},'','/dashboard/?theme=dark&view=activity');
  const observations:Observation[]=[];
  render(<ThemeProvider><Probe observations={observations}/></ThemeProvider>);
  expect(observations).toEqual([{state:'dark',applied:'dark'}]);
  expect(localStorage.getItem('toadaid_theme')).toBe('dark');
 });
 it('applies an interactive theme switch before descendant work observes the new state',() => {
  window.history.replaceState({},'','/dashboard/?theme=light');
  const observations:Observation[]=[];
  render(<ThemeProvider><Probe observations={observations}/></ThemeProvider>);
  fireEvent.click(screen.getByRole('button',{name:'Switch theme'}));
  expect(observations).toEqual([{state:'light',applied:'light'},{state:'dark',applied:'dark'}]);
 });
 it('retains the saved preference and operating-system fallback when storage is unavailable',() => {
  localStorage.setItem('toadaid_theme','light');
  const saved:Observation[]=[];
  const rendered=render(<ThemeProvider><Probe observations={saved}/></ThemeProvider>);
  expect(saved).toEqual([{state:'light',applied:'light'}]);
  rendered.unmount();
  vi.spyOn(Storage.prototype,'getItem').mockImplementation(() => {throw new Error('synthetic unavailable storage')});
  vi.spyOn(window,'matchMedia').mockReturnValue({matches:true} as MediaQueryList);
  const fallback:Observation[]=[];
  render(<ThemeProvider><Probe observations={fallback}/></ThemeProvider>);
  expect(fallback).toEqual([{state:'light',applied:'light'}]);
 });
});
