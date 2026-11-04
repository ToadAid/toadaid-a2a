import {describe,it,expect} from 'vitest';
import {render,screen,fireEvent} from '@testing-library/react';
import App from '../App';

describe('Agent Pond public navigation',()=>{
 it('links back to the hub, guide and Portal without forwarding query state',()=>{
  window.history.replaceState({},'','/dashboard/?view=security');render(<App/>);
  const nav=screen.getByRole('navigation',{name:'Agent Pond destinations'});
  expect(nav.querySelector('a[href="/"]')).not.toBeNull();
  expect(nav.querySelector('a[href="/pond/guide.md"]')).not.toBeNull();
  expect(nav.querySelector('a[href="https://portal.toadaid.org/a2a/"]')).toHaveAttribute('rel','noopener noreferrer');
 });
 it('keeps selected views in direct-link URLs and responds to browser history',()=>{
  window.history.replaceState({},'','/dashboard/');render(<App/>);
  fireEvent.click(screen.getByRole('tab',{name:/Agent Activity/}));expect(window.location.search).toBe('?view=activity');
  window.history.replaceState({},'','/dashboard/?view=security');fireEvent.popState(window);
  expect(screen.getByRole('tab',{name:/Security & Governance/})).toHaveAttribute('aria-selected','true');
 });
});
