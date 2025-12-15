import os
from pathlib import Path
from datetime import datetime
import gradio as gr
from github import Github, Auth
from git import Repo
import json
from slugify import slugify

# --- Configuration ---
HUGO_PROJECT_PATH = Path("/project")
CONTENT_AUTHORS_PATH = HUGO_PROJECT_PATH / "content/authors"
DATA_AUTHORS_PATH = HUGO_PROJECT_PATH / "data/authors"
CONTENT_BLOG_PATH = HUGO_PROJECT_PATH / "content/blog"
CLONE_PATH = HUGO_PROJECT_PATH / "repo_clone"
CODE_SERVER_BASE = "http://localhost:8087/"
REPO_FULL_NAME = "your-org/your-repo"

# Ensure directories exist
for path in [CONTENT_AUTHORS_PATH, DATA_AUTHORS_PATH, CONTENT_BLOG_PATH]:
    path.mkdir(parents=True, exist_ok=True)

# --- Helper Functions ---
def list_authors():
    return sorted([p.name for p in CONTENT_AUTHORS_PATH.iterdir() if p.is_dir()])

def format_author_name(name: str):
    return name.strip().replace(" ", "-").lower()

# --- Author Functions ---
def create_author(name):
    if not name or not name.strip():
        return "❌ Please enter a valid author name.", gr.update(), gr.update()
    
    name_formatted = format_author_name(name)
    author_dir = CONTENT_AUTHORS_PATH / name_formatted
    author_dir.mkdir(parents=True, exist_ok=True)
    
    (author_dir / "_index.md").write_text(f"---\ntitle: {name_formatted}\n---\n")
    (DATA_AUTHORS_PATH / f"{name_formatted}.json").write_text(
        json.dumps({"name": name_formatted, "bio": "", "image": ""}, indent=2)
    )
    
    authors = list_authors()
    status_msg = f"✅ Author '{name_formatted}' created! ({len(authors)} total)"
    update_choices = gr.update(choices=authors, value=name_formatted)
    return status_msg, update_choices, update_choices

def refresh_authors(default_author="espressif"):
    authors = list_authors()
    status_msg = f"🔄 Refreshed! ({len(authors)} authors)"
    # Use default_author if exists, else first author
    value = default_author if default_author in authors else (authors[0] if authors else None)
    update_choices = gr.update(choices=authors, value=value)
    return status_msg, update_choices, update_choices


# --- Article Function ---
def create_article(title, author_name):
    if not title or not author_name:
        return "❌ Please provide both title and author.", gr.update(), gr.update(visible=False), gr.update(visible=False)
    
    now = datetime.now()
    y, m = now.strftime("%Y"), now.strftime("%m")
    article_slug = slugify(title)
    article_dir = CONTENT_BLOG_PATH / y / m / article_slug
    article_dir.mkdir(parents=True, exist_ok=True)
    
    # Format date as YYYY-MM-DD only
    date_only = now.strftime("%Y-%m-%d")
    
    (article_dir / "index.md").write_text(f"""---
title: "{title}"
author: {author_name}
date: {date_only}
---
""")
    vscode_link = f"{CODE_SERVER_BASE}?folder=/project/content/blog/{y}/{m}/{article_slug}"
    preview_link = f"http://localhost:1313/blog/{y}/{m}/{article_slug}/"
    
    # Generate branch name
    branch_name = f"add/{article_slug}"
    
    # Return separate status message and VS Code link with styling
    status_msg = f"✅ Article '{title}' created by {author_name}."
    
    # Create styled link with chain emoji - red theme
    vscode_msg = f"""
    <div style="
        background: linear-gradient(135deg, #f56565 0%, #c53030 100%);
        padding: 12px 20px;
        border-radius: 8px;
        margin: 10px 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        border: 2px solid #742a2a;
    ">
        <a href="{vscode_link}" target="_blank" style="
            color: white;
            text-decoration: none;
            font-weight: bold;
            font-size: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        ">
            🔗 Open in VS Code
        </a>
    </div>
    """
    
    # Create styled preview link - orange theme
    preview_msg = f"""
    <div style="
        background: linear-gradient(135deg, #ed8936 0%, #dd6b20 100%);
        padding: 12px 20px;
        border-radius: 8px;
        margin: 10px 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        border: 2px solid #c05621;
    ">
        <a href="{preview_link}" target="_blank" style="
            color: white;
            text-decoration: none;
            font-weight: bold;
            font-size: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        ">
            👁️ Preview Article
        </a>
    </div>
    """
    
    return status_msg, gr.update(value=branch_name), vscode_msg, preview_msg

# --- Git Functions ---
def fork_repo(pat):
    try:
        g = Github(auth=Auth.Token(pat))
        user = g.get_user()
        repo = g.get_repo(REPO_FULL_NAME)
        fork = next((f for f in user.get_repos() if f.full_name.endswith(repo.name)), None)
        if not fork:
            fork = user.create_fork(repo)
        return f"✅ Forked repo: {fork.full_name}"
    except Exception as e:
        return f"❌ Fork failed: {str(e)}"

def clone_or_open_repo(pat):
    if CLONE_PATH.exists():
        return Repo(CLONE_PATH)
    g = Github(auth=Auth.Token(pat))
    user = g.get_user()
    repo_g = g.get_repo(REPO_FULL_NAME)
    fork = next((f for f in user.get_repos() if f.full_name.endswith(repo_g.name)), None)
    if not fork:
        fork = user.create_fork(repo_g)
    Repo.clone_from(fork.ssh_url, CLONE_PATH)
    return Repo(CLONE_PATH)

def create_branch(branch_name, pat):
    try:
        repo = clone_or_open_repo(pat)
        repo.git.checkout('HEAD', b=branch_name)
        return f"✅ Branch '{branch_name}' created."
    except Exception as e:
        return f"❌ Branch failed: {str(e)}"

def commit_changes(message, pat):
    try:
        repo = clone_or_open_repo(pat)
        repo.git.add(A=True)
        repo.index.commit(message)
        return f"✅ Committed: '{message}'"
    except Exception as e:
        return f"❌ Commit failed: {str(e)}"

def push_changes(branch_name, pat):
    try:
        repo = clone_or_open_repo(pat)
        origin = repo.remote(name='origin')
        origin.push(refspec=f"{branch_name}:{branch_name}")
        return f"✅ Pushed '{branch_name}'"
    except Exception as e:
        return f"❌ Push failed: {str(e)}"

# --- Gradio UI ---
with gr.Blocks(title="Developer portal article manager", css="""
    .vscode-link-container {
        margin: 10px 0;
        padding: 12px 20px;
        background: linear-gradient(135deg, #f56565 0%, #c53030 100%);
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        border: 2px solid #742a2a;
    }
    .vscode-link {
        color: white !important;
        text-decoration: none !important;
        font-weight: bold !important;
        font-size: 16px !important;
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
    }
    .vscode-link:hover {
        color: #fed7d7 !important;
        text-decoration: underline !important;
    }
    .preview-link-container {
        margin: 10px 0;
        padding: 12px 20px;
        background: linear-gradient(135deg, #ed8936 0%, #dd6b20 100%);
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        border: 2px solid #c05621;
    }
    .preview-link {
        color: white !important;
        text-decoration: none !important;
        font-weight: bold !important;
        font-size: 16px !important;
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
    }
    .preview-link:hover {
        color: #feebc8 !important;
        text-decoration: underline !important;
    }
""") as demo:
    gr.Markdown("# 🚀 Developer portal article manager")
    
    # Status outputs
    author_status = gr.Markdown()
    article_output = gr.Markdown()
    git_output = gr.Markdown()
    
    # Author dropdown (outside accordion)
    existing_author_dd = gr.Dropdown(label="Select Author", choices=[], interactive=True)
    
    # New Author Section - in an accordion
    with gr.Accordion("New Author", open=False) as new_author_accordion:
        with gr.Row():
            with gr.Column(scale=2):
                new_author_tb = gr.Textbox(label="New Author Name", placeholder="New author...")
                create_author_btn = gr.Button("➕ Create Author", variant="primary")
            with gr.Column(scale=1):
                refresh_btn = gr.Button("🔄 Refresh", variant="secondary")
    
    # Article Section
    with gr.Row():
        article_title_tb = gr.Textbox(label="Article Title", placeholder="My first post...")
        with gr.Column():
            create_article_btn = gr.Button("📝 Create Article", variant="stop")
            vscode_link_output = gr.HTML()
            preview_link_output = gr.HTML()
    
    # Git Section
    with gr.Accordion("Git Operations", open=False):
        with gr.Row():
            pat_tb = gr.Textbox(label="GitHub PAT", type="password")
            branch_tb = gr.Textbox(label="Branch", placeholder="feature/blog")
        msg_tb = gr.Textbox(label="Commit Msg", value="Add authors/articles")
        with gr.Row():
            gr.Button("🍴 Fork").click(fork_repo, [pat_tb], git_output)
            gr.Button("🌿 Branch").click(create_branch, [branch_tb, pat_tb], git_output)
            gr.Button("💾 Commit").click(commit_changes, [msg_tb, pat_tb], git_output)
            gr.Button("⬆️ Push", variant="stop").click(push_changes, [branch_tb, pat_tb], git_output)
    
    # Connect buttons to functions
    create_author_btn.click(
        create_author,
        inputs=[new_author_tb],
        outputs=[author_status, existing_author_dd, existing_author_dd]
    )
    
    refresh_btn.click(
        refresh_authors,
        inputs=None,
        outputs=[author_status, existing_author_dd, existing_author_dd]
    )
    
    create_article_btn.click(
        create_article, 
        inputs=[article_title_tb, existing_author_dd], 
        outputs=[article_output, branch_tb, vscode_link_output, preview_link_output]
    )

    # ✅ Populate dropdown at startup
    demo.load(
        lambda: refresh_authors("espressif"),
        inputs=None,
        outputs=[author_status, existing_author_dd, existing_author_dd]
    )

demo.launch(server_name="0.0.0.0", server_port=7860, debug=True)
