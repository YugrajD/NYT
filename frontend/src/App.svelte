<script lang="ts">
  import { onMount } from 'svelte';
  import logo from './assets/Logo.png';

  type Doc = {
    headline: { main: string };
    snippet: string;
    web_url: string;
    multimedia: {
      default: { url: string };
      thumbnail: { url: string };
    };
  };

  let articles: Doc[] = [];
  let pageNum = 0;
  let loading = false;
  let moreArticles = true;
  let user: any = null;
  let showSidebar = false;
  let selectedArticle: Doc | null = null;
  let commentText = '';
  let comments: { user: string; text: string }[] = [];

  async function loadArticles() {
    if (loading || !moreArticles) return;
    loading = true;
    try {
      const res = await fetch(`/api/articles?page=${pageNum}`, { credentials: 'include' });
      const { response } = await res.json();
      const newArticles = response?.docs || [];
      if (newArticles.length === 0) {
        moreArticles = false;
      } else {
        articles = [...articles, ...newArticles];
        pageNum += 1;
      }
    } catch (err) {
      console.error('Error loading NYT articles:', err);
    } finally {
      loading = false;
    }
  }

  async function fetchComments(url: string) {
    const res = await fetch(`/api/comments?url=${encodeURIComponent(url)}`);
    comments = await res.json();
  }

  async function postComment() {
    if (!commentText.trim()) return;
    await fetch('/api/comments', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url: selectedArticle?.web_url,
        user: user?.email ?? 'anonymous',
        text: commentText
      })
    });
    commentText = '';
    fetchComments(selectedArticle?.web_url || '');
  }

  onMount(async () => {
    try {
      const res = await fetch('/api/me', { credentials: 'include' });
      if (res.ok) user = await res.json();
    } catch (e) {
      console.error('Failed to fetch user:', e);
    }

    loadArticles();

    if (typeof IntersectionObserver !== 'undefined') {
      const observer = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting) {
          loadArticles();
        }
      }, { threshold: 1.0 });

      const sentinel = document.getElementById('sentinel');
      if (sentinel) observer.observe(sentinel);
    }
  });
</script>

<header>
  <div class="header-row">
    <div class="header-center-logo">
      <img src={logo} alt="NYT Logo" id="logo" class="center" />
    </div>
    <div class="header-left-text">
      <p><strong>{new Date().toDateString()}</strong></p>
      <p>Today's Paper</p>
    </div>
    <div class="header-right-auth">
      {#if user}
        <button class="auth-button" on:click={() => showSidebar = !showSidebar}>
          Account ▾
        </button>
      {:else}
        <a class="auth-button" href="/login">
          Log In
        </a>
      {/if}
    </div>
  </div>
</header>

<hr />

<main>
  <div class="grid-container">
    {#each articles as article, i}
      {#if i > 0 && i % 3 === 0}
        <hr class="divider" />
      {/if}
      <section class="column column-{String.fromCharCode(97 + i)}">
        {#if article.multimedia?.default?.url}
          <img src={article.multimedia.default.url} alt={article.headline.main} style="max-width:100%;height:auto;" />
        {:else}
          <p class="no-image">No image available</p>
        {/if}
        <h2>{article.headline.main}</h2>
        <p>{article.snippet}</p>
        <button
        class="comment-button"
        on:click={async () => {
          selectedArticle = article;
          await fetchComments(article.web_url);
        }}>
        Comments ({comments.length})
      </button>
      
         
        <a href={article.web_url} target="_blank" rel="noopener">Read More</a>
      </section>
    {/each}
    {#if articles.length === 0}
      <p class="no-articles">No articles to show.</p>
    {/if}
  </div>
  <div id="sentinel" style="height: 50px;"></div>
</main>

{#if showSidebar}
  <div class="sidebar-overlay" on:click={() => showSidebar = false}></div>
  <aside class="sidebar">
    <div class="sidebar-header">
      <strong>{user?.email}</strong>
      <button class="close-btn" on:click={() => showSidebar = false}>×</button>
    </div>
    <p>Good afternoon.</p>
    <a class="logout-button" href="/logout">Log out 🖕🏽</a>
  </aside>
{/if}

{#if selectedArticle}
  <div class="comment-drawer-overlay" on:click={() => selectedArticle = null}></div>
  <aside class="comment-drawer">
    <div class="drawer-header">
      <h3>{selectedArticle.headline.main}</h3>
      <button class="close-btn" on:click={() => selectedArticle = null}>×</button>
    </div>
    <h4>Comments {comments.length}</h4>
    <input
      placeholder="Share your thoughts..."
      bind:value={commentText}
      on:keydown={(e) => e.key === 'Enter' && postComment()}
    />
    <div class="comment-list">
      {#each comments as c}
        <div class="comment-item">
          <strong>{c.user}</strong>
          <p>{c.text}</p>
        </div>
      {/each}
    </div>
  </aside>
{/if}
<style>
.center {
  padding-top: 20px;
  display: block;
  margin-left: auto;
  margin-right: auto;
  width: 50%;
}

h2 {
  font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
  font-size: 13px;
  text-indent: 10px;
}

h3 {
  font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
  font-size: 13px;
  text-indent: 10px;
  font-weight: lighter;
}

.grid-container {
  display: grid;
  gap: 20px;
  grid-template-columns: repeat(3, 1fr);
  padding: 20px;
  font-family: Georgia;
}

.column {
  position: relative;
  padding: 20px;
  border-right: 1px solid black;
  height: auto;
}

.column:last-child {
  border-right: none;
}

.divider {
  grid-column: 1 / -1;
  border-top: 1px solid black;
  margin: 20px 0;
}

.header-row {
  position: relative;
}

.header-right-auth {
  position: absolute;
  top: 20px;
  right: 20px;
}

.auth-button {
  background-color: #326891;
  color: white;
  padding: 6px 12px;
  border-radius: 4px;
  text-decoration: none;
  font-weight: bold;
  font-size: 14px;
}

.auth-button:hover {
  background-color: #244f6d;
}

.sidebar-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background-color: rgba(0, 0, 0, 0.3);
  z-index: 999;
}

.sidebar {
  position: fixed;
  top: 0;
  right: 0;
  width: 260px;
  height: 100%;
  background-color: white;
  padding: 20px;
  box-shadow: -2px 0 5px rgba(0,0,0,0.2);
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.close-btn {
  background: none;
  border: none;
  font-size: 22px;
  cursor: pointer;
}

.logout-button {
  background-color: #326891;
  color: white;
  padding: 6px 12px;
  border-radius: 4px;
  text-decoration: none;
  font-weight: bold;
  font-size: 14px;
}

.logout-button:hover {
  background-color: #244f6d;
}

@media only screen and (min-width: 1024px) {
  .grid-container {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media only screen and (min-width: 768px) and (max-width: 1024px) {
  .grid-container {
    grid-template-columns: repeat(2, 1fr);
  }
  .column:nth-last-child(2) {
    border-right: white;
  }
  .column:last-child {
    display: none;
  }
}

@media only screen and (max-width: 768px) {
  .grid-container {
    grid-template-columns: repeat(1, 1fr);
  }
  .column {
    border-right: white;
  }
  .column:nth-last-child(2),
  .column:last-child {
    display: none;
  }
}

.comment-button {
  position: absolute;
  bottom: 10px;
  right: 10px;
  background-color: #eee;
  border: 1px solid #ccc;
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  font-weight: 500;
}

.comment-button:hover {
  background-color: #ddd;
}


.comment-drawer {
  position: fixed;
  top: 0;
  right: 0;
  width: 400px;
  max-width: 90%;
  height: 100%;
  background: white;
  box-shadow: -2px 0 5px rgba(0, 0, 0, 0.2);
  padding: 20px;
  z-index: 1001;
  display: flex;
  flex-direction: column;
}

.comment-drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
  font-size: 18px;
  border-bottom: 1px solid #ccc;
  padding-bottom: 10px;
}

.comment-drawer-header button {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
}

.comment-list {
  flex: 1;
  overflow-y: auto;
  margin-top: 15px;
}

.comment {
  border-bottom: 1px solid #eee;
  padding: 10px 0;
}

.comment strong {
  display: block;
  font-size: 14px;
  margin-bottom: 4px;
}

.comment p {
  font-size: 13px;
  margin: 0;
}

.comment-input {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 20px;
}

.comment-input textarea {
  width: 100%;
  min-height: 60px;
  font-size: 14px;
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
  resize: vertical;
}

.comment-input button {
  align-self: flex-end;
  padding: 6px 12px;
  background-color: #326891;
  color: white;
  border: none;
  border-radius: 4px;
  font-weight: bold;
  cursor: pointer;
}

.comment-input button:hover {
  background-color: #244f6d;
}

</style>