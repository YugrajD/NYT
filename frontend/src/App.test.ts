// <reference types="vitest-environment-jsdom" />

import { expect, test, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/svelte';
import App from './App.svelte';
  
vi.stubGlobal('fetch', vi.fn(() =>
    Promise.resolve({
      json: () => Promise.resolve({ response: { docs: [] } })
    })
  ));

test('Renders without errors', () => {
    const { container } = render(App);
    expect(container).toBeTruthy();
});

test('Contains a header element', () => {
    const { container } = render(App);
    const header = container.querySelector('header');
    expect(header).not.toBeNull();
});

test('Contains a main element', () => {
    const { container } = render(App);
    const main = container.querySelector('main');
    expect(main).not.toBeNull();
});

test('Contains an image with NYT logo', () => {
    render(App);
    const logoImg = document.querySelector('img[alt="NYT Logo"]');
    expect(logoImg).not.toBeNull();
});

test('Does the date match', () => {
    const today = new Date().toDateString();
    const { container } = render(App);
    expect(container.textContent).toContain(today);
  });
  

test('Grid layout is responsive', () => {
    const { container } = render(App);
    const grid = container.querySelector('.grid-container');
    expect(grid).not.toBeNull();
  });

  test('Shows Account button when user is logged in', async () => {
    vi.stubGlobal('fetch', vi.fn((url) => { // Mock fetch for user data
      if (url.includes('/api/me')) return Promise.resolve({ ok: true, json: () => Promise.resolve({ email: 'user@example.com' }) });
      return Promise.resolve({ json: () => Promise.resolve({}) });
    }));
    const { findByText } = render(App);
    const accountButton = await findByText('Account ▾');
    expect(accountButton).not.toBeNull(); // Check if the button is present
    expect(accountButton.textContent).toBe('Account ▾');
  });

  test('Shows sidebar with user email when Account button is clicked', async () => {
    vi.stubGlobal('fetch', vi.fn((url) => { // Mock fetch for user data
      if (url.includes('/api/me')) return Promise.resolve({ ok: true, json: () => Promise.resolve({ email: 'user@example.com' }) });
      return Promise.resolve({ json: () => Promise.resolve({}) });
    }));
    const { getByText, findByText } = render(App);
    const accountButton = getByText('Account ▾');
    await fireEvent.click(accountButton); // Open the account dropdown
    const userEmail = await findByText('user@example.com');
    expect(userEmail).not.toBeNull();
  });

  test('Opens comment drawer and fetches comments when Comments button is clicked', async () => {
    const mockArticles = { response: { docs: [{ headline: { main: 'Test Article 1' }, web_url: 'http://example.com/1' }] } };
    vi.stubGlobal('fetch', vi.fn((url) => { // Mock fetch for articles and comments
      if (url.includes('/api/articles')) return Promise.resolve({ json: () => Promise.resolve(mockArticles) });
      if (url.includes('/api/comments')) return Promise.resolve({ json: () => Promise.resolve([{ _id: '1', text: 'Great article!' }]) });
      return Promise.resolve({ json: () => Promise.resolve({}) });
    }));
    const { findByText, findByRole } = render(App);
    const commentsButton = await findByText('Comments (0)');
    await fireEvent.click(commentsButton); // Open the comments drawer
    const headline = await findByRole('heading', { name: 'Test Article 1', level: 3 });
    expect(headline).not.toBeNull();
  });
