<script lang="ts">
  import { onMount } from 'svelte';
  import logo from './assets/Logo.png';

  // Article structure
  type Doc = {
    headline: { main: string };
    snippet: string;
    web_url: string;
    multimedia: {
      default: { url: string }; // high quality image
      thumbnail: { url: string }; // low quality/thumbnail image
    };
  };
  // Comment structure
  type Comment = {
    _id: string;         // ID from mongo
    user: string;        // email of user
    text: string;        
    parentId?: string;   // This is needed for repleis 
    removed?: boolean;   // this lets us know if the comment is deleted
  };

  // article loading state
  let articles: Doc[] = [];        // stores the articles 
  let pageNum = 0;                 // the current page number for pagination
  let loading = false;             // prevents multiple simultaneous requests
  let moreArticles = true;         // boolean to check if more articles are available
  // User state
  let user: any = null;            // info of the logged-in user
  let showSidebar = false;         // is the sidebar open?
  let selectedArticle: Doc | null = null;  // currently selected article 
  // Comment system state
  let commentText = '';            // text for the new comment
  let comments: Comment[] = [];    // all stored comments of that article
  let commentCounts: Record<string, number> = {};  // how many comments are there
  let replyingTo: string | null = null;            // ID of the comment that is being replied to 
  let replyTexts: Record<string, string> = {};     // what is in the reply 
  // Loads articles from the API
  async function loadArticles() {
    if (loading || !moreArticles) return;  // stops if already loading or no more articles
    loading = true;
    try {
      const res = await fetch(`/api/articles?page=${pageNum}`, { credentials: 'include' }); // fetch articles
      const { response } = await res.json();
      const newArticles = response?.docs || [];
      
      // Check for new articles
      if (!newArticles.length) moreArticles = false;
      else {
        // push new articles to the existing list
        articles = [...articles, ...newArticles];
        pageNum += 1; 
      }
    } catch (err) {
      console.error(err);
    } finally {
      loading = false;
    }
  }

  // fetch all the comment counts for articles
  async function fetchAllCounts() {
    const res = await fetch('/api/comment-counts');
    commentCounts = await res.json();
  }

  // this is to fetch comments for a specific article
  async function fetchComments(url: string) {
    const res = await fetch(`/api/comments?url=${encodeURIComponent(url)}`, { credentials: 'include' });
    comments = await res.json();
    
    // initialize replyTexts for each comment
    comments.forEach(c => {
      if (!(c._id in replyTexts)) replyTexts[c._id] = '';
    });
    
    // reset replyingTo
    replyingTo = null;
  }

  // post the top level comment
  async function postComment() {
    if (!commentText.trim() || !selectedArticle) return;
    
    await fetch('/api/comments', {  // post comment
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url: selectedArticle!.web_url,
        user: user?.email ?? 'anonymous', // use email if logged in
        text: commentText
      })
    });
    
    // clear the comment text and refresh comments
    commentText = '';
    await fetchComments(selectedArticle!.web_url);
    commentCounts[selectedArticle!.web_url] = comments.length;
  }

  // this is to post a reply to a comment
  async function postReply(parentId: string) {
    const text = replyTexts[parentId];
    if (!text?.trim() || !selectedArticle) return;
    
    await fetch('/api/comments', { // post reply 
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url: selectedArticle!.web_url,
        user: user?.email ?? 'anonymous', // use email if logged in
        text,
        parentId  // include parent ID to mark as reply
      })
    });
    
    // same thing, clear the reply text and refresh comments
    replyTexts[parentId] = '';
    replyingTo = null;
    await fetchComments(selectedArticle!.web_url);
    commentCounts[selectedArticle!.web_url] = comments.length;
  }

  // MODERATOR: delete a comment
  async function deleteComment(id: string) {
    if (!confirm('Are you sure?')) return;
    
    await fetch(`/api/comments/${id}`, {
      method: 'DELETE', // calls for a delete request
      credentials: 'include'
    });
    
    // refresh comments
    if (selectedArticle) {
      await fetchComments(selectedArticle.web_url);
      await fetchAllCounts();
    }
  }

  // Helper: filters comments to get top-level comments (no parentId)
  function topLevel() {
    return comments.filter(c => !c.parentId);
  }
  
  // Helper: filters comments to get replies to a specific comment (parentId) they have a parentID if they are replies
  function repliesForward(id: string) {
    return comments.filter(c => c.parentId === id);
  }

  // initial setup
  onMount(async () => {
    // Check if user is logged in
    try {
      const me = await fetch('/api/me', { credentials: 'include' });
      if (me.ok) user = await me.json();
    } catch {}
    
    // load initial articles and comment counts
    await loadArticles();
    await fetchAllCounts();
    
    // infinite scroll setup
    if ('IntersectionObserver' in window) {
      const obs = new IntersectionObserver(
        ([e]) => e.isIntersecting && loadArticles(),
        { threshold: 1.0 }
      );
      const sentinel = document.getElementById('sentinel');
      sentinel && obs.observe(sentinel);
    }
  });
</script>

<header>
  <div class="header-row">
    <div class="header-center-logo">
      <!-- NYT logo centered at the top -->
      <img src={logo} alt="NYT Logo" class="center" />
    </div>
    <div class="header-left-text">
      <!-- Current date display -->
      <p><strong>{new Date().toDateString()}</strong></p>
      <p>Today's Paper</p>
    </div>
    <div class="header-right-auth">
      <!-- Conditional authentication UI -->
      {#if user}
        <button class="auth-button" on:click={() => showSidebar = !showSidebar}>
          Account ▾
        </button>
      {:else}
        <a class="auth-button" href="/login">Log In</a>
      {/if}
    </div>
  </div>
</header>

<hr />

<main>
  <div class="grid-container">
    <!-- Loop through articles and display in grid -->
    {#each articles as article, i}
      <!-- Add divider after every 3 articles -->
      {#if i > 0 && i % 3 === 0}
        <hr class="divider" />
      {/if}
      <!-- Article column with a-z class for styling -->
      <section class="column column-{String.fromCharCode(97 + i)}">
        <!-- Display article image if available -->
        {#if article.multimedia?.default?.url}
          <img src={article.multimedia.default.url} alt={article.headline.main} style="max-width:100%;height:auto;" />
        {:else}
          <p class="no-image">No image available</p>
        {/if}
        <!-- Article title and snippet -->
        <h2>{article.headline.main}</h2>
        <p>{article.snippet}</p>
        <!-- Comment button with count -->
         
        <button
          class="comment-button"
          on:click={async () => {
            selectedArticle = article;
            await fetchComments(article.web_url);
          }}>
          Comments ({commentCounts[article.web_url] || 0})
        </button>
        <!-- Link to full article -->
        <a href={article.web_url} target="_blank" rel="noopener">Read More</a>
      </section>
    {/each}
    <!-- Message when no articles available -->
    {#if !articles.length}
      <p class="no-articles">No articles to show.</p>
    {/if}
  </div>
  <!-- Sentinel element for infinite scroll detection -->
  <div id="sentinel" style="height:50px;"></div>
</main>

<!-- User account sidebar (shown when toggled) -->
{#if showSidebar}
  <div class="sidebar-overlay" on:click={() => showSidebar = false}></div>
  <aside class="sidebar">
    <div class="sidebar-header">

      <!-- Sidebar header with user info (email) -->
      <strong>{user?.email}</strong>
      <button class="close-btn" on:click={() => showSidebar = false}>×</button>
    </div>
    <p>Good afternoon.</p>
    <a class="logout-button" href="/logout">Log out</a>
  </aside>
{/if}

<!-- Comment drawer for selected article -->
{#if selectedArticle}
  <div class="comment-drawer-overlay" on:click={() => {
    selectedArticle = null; 
    replyingTo = null;
  }}></div>
  <aside class="comment-drawer">
    <!-- Drawer header with article title -->
    <div class="drawer-header">
      <h3>{selectedArticle.headline.main}</h3>
      <button class="close-btn" on:click={() => {
        selectedArticle = null; 
        replyingTo = null;

      }}>×</button>
    </div>
    <!-- Comment count and input field -->
    <h4>Comments ({comments.length})</h4>
    <input
      class="comment-input"
      placeholder="Comment"
      bind:value={commentText}
      on:keydown={(e) => e.key === 'Enter' && postComment()}
    />
    <!-- List of comments -->
    <div class="comment-list">
      {#each topLevel() as c (c._id)}
        <div class="comment-item">
          <strong>{c.user}</strong>

          {#if c.removed}
            <!-- Display for soft-deleted comments, let the user know there was a comment -->
            <p><em>COMMENT REMOVED BY MODERATOR!</em></p>
          {:else}
            <!-- Normal comment display -->
            <p>{c.text}</p>
            <!-- Comment controls (reply/moderate) -->
            <div class="comment-controls">

              {#if user}
                <button class="reply-btn" on:click={() => replyingTo = c._id}>Reply</button>
              {/if}

              <!-- Only show delete button for moderator -->
              {#if user?.email === 'moderator@hw3.com'}
                <button class="delete-btn" on:click={() => deleteComment(c._id)}>Delete</button>
              {/if}
            </div>
          {/if}
          <!-- Reply input box (shown when click reply) -->
          {#if replyingTo === c._id}
            <div class="reply-box">
              <input placeholder="Reply" bind:value={replyTexts[c._id]} />
              <button on:click={() => postReply(c._id)}>Submit</button>
            </div>

          {/if}
          <!-- Nested replies for the comment -->
          {#each repliesForward(c._id) as reply (reply._id)}
            <div class="reply-item">
              <strong>{reply.user}</strong>
              {#if reply.removed}
                <p><em>COMMENT REMOVED BY MODERATOR!</em></p>

              {:else}
                <p>{reply.text}</p>
                <div class="comment-controls">
                  <!-- Reply button for nested replies -->
                  {#if user}
                    <button class="reply-btn" on:click={() => replyingTo = reply._id}>Reply</button>
                  {/if}

                  {#if user?.email === 'moderator@hw3.com'}
                    <button class="delete-btn" on:click={() => deleteComment(reply._id)}>Delete</button>
                   
                  {/if}
                </div>
              {/if}
                <!-- creates a nested reply box -->
              {#if replyingTo === reply._id}
                <div class="reply-box">
                  <input placeholder="Reply" bind:value={replyTexts[reply._id]} />
                  <button on:click={() => postReply(reply._id)}>Submit</button>
                </div>
              {/if}
            </div>
          {/each}
        </div>
      {/each}
    </div>
  </aside>
{/if}

<style>
/* NYT Logo styling */
.center {
  padding-top: 20px;
  display: block;
  margin-left: auto;
  margin-right: auto;
  width: 50%;
}

/* Article headline styling */
h2 {
  font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
  font-size: 13px;
  text-indent: 10px;
}

/* Secondary heading styling */
h3 {
  font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
  font-size: 13px;
  text-indent: 10px;
  font-weight: lighter;
}

/* Grid layout for articles */
.grid-container {
  display: grid;
  gap: 20px;
  grid-template-columns: repeat(3, 1fr);
  padding: 20px;
  font-family: Georgia;
}

/* Styling for each article column */
.column {
  position: relative;
  padding: 20px;
  border-right: 1px solid black;
  height: auto;
}

/* Remove border from the last column */
.column:last-child {
  border-right: none;
}

/* Horizontal dividers between article rows */
.divider {
  grid-column: 1 / -1;
  border-top: 1px solid black;
  margin: 20px 0;
}

/* Header layout */
.header-row {
  position: relative;
}

/* Authentication button positioning */
.header-right-auth {
  position: absolute;
  top: 20px;
  right: 20px;
}

/* Authentication button styling */
.auth-button {
  background-color: #326891;
  color: white;
  padding: 6px 12px;
  border-radius: 4px;
  text-decoration: none;
  font-weight: bold;
  font-size: 14px;
}

/* Authentication button hover effect */
.auth-button:hover {
  background-color: #244f6d;
}

/* Overlay for sidebar */
.sidebar-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background-color: rgba(0, 0, 0, 0.3);
  z-index: 999;
}

/* Sidebar styling */
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

/* Sidebar header with user info */
.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* Close button for sidebar and drawer */
.close-btn {
  background: none;
  border: none;
  font-size: 22px;
  cursor: pointer;
}

/* Logout button styling */
.logout-button {
  background-color: #326891;
  color: white;
  padding: 6px 12px;
  border-radius: 4px;
  text-decoration: none;
  font-weight: bold;
  font-size: 14px;
}

/* Logout button hover effect */
.logout-button:hover {
  background-color: #244f6d;
}

/* Responsive layout: desktop view */
@media only screen and (min-width: 1024px) {
  .grid-container {
    grid-template-columns: repeat(3, 1fr);
  }
}

/* Responsive layout: tablet view */
@media only screen and (min-width: 768px) and (max-width: 1024px) {
  .grid-container {
    grid-template-columns: repeat(2, 1fr);
  }
  .column:nth-last-child(2) {
    border-right: none;
  }
  .column:last-child {
    display: none;
  }
}

/* Responsive layout: mobile view */
@media only screen and (max-width: 768px) {
  .grid-container {
    grid-template-columns: repeat(1, 1fr);
  }
  .column {
    border-right: none;
  }
  .column:nth-last-child(2),
  .column:last-child {
    display: none;
  }
}

/* Comment button styling */
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

/* Comment button hover effect */
.comment-button:hover {
  background-color: #ddd;
}

/* Comment drawer styling */
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

/* Comment list container */
.comment-list {
  flex: 1;
  overflow-y: auto;
  margin-top: 15px;
}

/* Comment input field */
.comment-input {
  margin-top: 20px;
  padding: 8px;
  font-size: 14px;
  border: 1px solid #ccc;
  border-radius: 4px;
}

/* Reply button styling */
.reply-btn {
  margin-top: 4px;
  background: none;
  border: none;
  color: #326891;
  cursor: pointer;
  font-size: 13px;
}

/* Reply input box styling */
.reply-box {
  margin-top: 6px;
  display: flex;
  gap: 6px;
}

/* Input field within reply box */
.reply-box input {
  flex: 1;
  padding: 4px;
  font-size: 13px;
}

/* Reply comment styling with indentation */
.reply-item {
  margin-left: 20px;
  padding-left: 10px;
  border-left: 2px solid #ccc;
  margin-top: 8px;
}

/* Delete button styling */
.delete-btn {
  margin-top: 4px;
  background: none;
  border: none;
  color: red;
  cursor: pointer;
  font-size: 13px;
}

/* Container for comment control buttons */
.comment-controls {
  display: flex;
  gap: 10px;
  margin-top: 4px;
}
</style>