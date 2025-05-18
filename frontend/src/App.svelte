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

  async function loadArticles() {
    if (loading || !moreArticles) return;
    loading = true;
    try {
      const res = await fetch(`/api/articles?page=${pageNum}`); 
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

  onMount(() => {
    if (typeof window !== 'undefined') {
      loadArticles();

      if (typeof IntersectionObserver !== 'undefined') {
        const observer = new IntersectionObserver((entries) => {
          if (entries[0].isIntersecting) {
            loadArticles(); 
          }
        }, {
          threshold: 1.0
        });

        const sentinel = document.getElementById('sentinel');
        if (sentinel) observer.observe(sentinel);
      }
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
      <!-- this will hit your Flask /login route -->
        <a class="auth-button" href="/login">
           Log In
          </a>
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
          <img
            src={article.multimedia.default.url}
            alt={article.headline.main}
            style="max-width:100%;height:auto;"
          />
        {:else}
          <p class="no-image">No image available</p>
        {/if}
        <h2>{article.headline.main}</h2>
        <p>{article.snippet}</p>
        <a href={article.web_url} target="_blank" rel="noopener">Read More</a>
      </section>
    {/each}
    {#if articles.length === 0}
      <p class="no-articles">No articles to show.</p>
    {/if}
  </div>
  <div id="sentinel" style="height: 50px;"></div>
</main>

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
</style>
