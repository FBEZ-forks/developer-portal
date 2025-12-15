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
REPO_FULL_NAME = "your-org/your-repo"  # Replace with your repo

# Ensure directories exist
CONTENT_AUTHORS_PATH.mkdir(parents=True, exist_ok=True)
DATA_AUTHORS_PATH.mkdir(parents=True, exist_ok=True)
CONTENT_BLOG_PATH.mkdir(parents=True, exist_ok=True)

# --- Helper Functions ---
def list_authors():
    return sorted([p.name for p in CONTENT_AUTHORS_PATH.iterdir() if p.is_dir()])

def format_author_name(name: str):
    return name.strip().replace(" ", "-").lower()

def create_author(name):
    if not name or not name.strip():
        return "❌ Please enter a valid author name.", {"choices": [], "value": None}
    
    # Format and create author
    name_formatted = format_author_name(name)
    author_dir = CONTENT_AUTHORS_PATH / name_formatted
    author_dir.mkdir(parents=True, exist_ok=True)
    
    index_md = author_dir / "_index.md"
    index_md.write_text(f"---\ntitle: {name_formatted}\n---\n")
    
    json_file = DATA_AUTHORS_PATH / f"{name_formatted}.json"
    json_file.write_text(json.dumps({"name": name_formatted, "bio": "", "image": ""}, indent=2))
    
    # ✅ FIXED: Plain dictionary for Gradio 4.x+
    authors = list_authors()
    return (
        f"✅ Author '{name_formatted}' created successfully!",
        {"choices": authors, "value": name_formatted}
    )

def slug(text):
    return slugify(text)

def create_article(title, author_name):
    if not title or not author_name:
        return "❌ Please provide both title and author."
    
    now = datetime.now()
    y, m = now.strftime("%Y"), now.strftime("%m")
    article_slug = slug(title)
    article_dir = CONTENT_BLOG_PATH / y / m / article_slug
    article_dir.mkdir(parents=True, exist_ok=True)
    index_md = article_dir / "index.md"
    index_md.write_text(f"""---
title: "{title}"
author: {author_name}
date: {now.isoformat()}
---
""")
    vscode_link = f"{CODE_SERVER_BASE}?folder=/project/content/blog/{y}/{m}/{article_slug}"
    return f"✅ Article '{title}' created by {author_name}.\n\n[👉 Open in VS Code]({vscode_link})"

# --- Git Functions ---
def fork_repo(pat):
    try:
        g = Github(auth=Auth.Token(pat))
        user = g.get_user()
        repo = g.get_repo(REPO_FULL_NAME)
        fork = None
        for f in user.get_repos():
            if f.full_name.endswith(repo.name):
                fork = f
                break
        if not fork:
            fork = user.create_fork(repo)
        return f"✅ Forked repo: {fork.full_name}"
    except Exception as e:
        return f"❌ Fork failed: {str(e)}"

def clone_or_open_repo(pat):
    if CLONE_PATH.exists():
        return Repo(CLONE_PATH)
    else:
        g = Github(auth=Auth.Token(pat))
        user = g.get_user()
        repo_g = g.get_repo(REPO_FULL_NAME)
        fork = None
        for f in user.get_repos():
            if f.full_name.endswith(repo_g.name):
                fork = f
                break
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
        return f"❌ Branch creation failed: {str(e)}"

def commit_changes(message, pat):
    try:
        repo = clone_or_open_repo(pat)
        repo.git.add(A=True)
        repo.index.commit(message)
        return f"✅ Committed changes with message: '{message}'"
    except Exception as e:
        return f"❌ Commit failed: {str(e)}"

def push_changes(branch_name, pat):
    try:
        repo = clone_or_open_repo(pat)
        origin = repo.remote(name='origin')
        origin.push(refspec=f"{branch_name}:{branch_name}")
        return f"✅ Pushed branch '{branch_name}' to origin"
    except Exception as e:
        return f"❌ Push failed: {str(e)}"

def refresh_authors():
    authors = list_authors()
    return {"choices": authors, "value": authors[0] if authors else None}

# --- Gradio UI ---
with gr.Blocks(title="Hugo Blog Manager", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🚀 Hugo Blog Manager (Git Decoupled)")
    gr.Markdown("Create authors, articles, and manage your Hugo blog with Git integration.")

    # Status output for authors
    author_status = gr.Markdown()

    # Author Section
    with gr.Row():
        with gr.Column(scale=2):
            new_author_tb = gr.Textbox(
                label="New Author Name", 
                placeholder="Enter new author name..."
            )
            create_author_btn = gr.Button("➕ Create Author", variant="primary")
        
        with gr.Column(scale=1):
            refresh_btn = gr.Button("🔄 Refresh Authors", variant="secondary")
    
    existing_author_dd = gr.Dropdown(
        label="Select Existing Author", 
        choices=list_authors(),
        allow_custom_value=False
    )
    
    # Article Section
    with gr.Row():
        article_title_tb = gr.Textbox(label="Article Title", placeholder="Enter article title...")
        create_article_btn = gr.Button("📝 Create Article", variant="primary")
    
    article_output = gr.Markdown()

    # Git Section
    with gr.Accordion("Git Operations", open=False):
        gr.Markdown("### GitHub Fork & Push Workflow")
        with gr.Row():
            pat_tb = gr.Textbox(label="GitHub PAT", type="password")
            branch_name_tb = gr.Textbox(label="Branch Name", placeholder="feature/new-blog")
        
        commit_message_tb = gr.Textbox(
            label="Commit Message", 
            placeholder="Add new authors and articles",
            value="Add new authors and articles"
        )
        
        with gr.Row():
            fork_btn = gr.Button("🍴 Fork Repo")
            branch_btn = gr.Button("🌿 Create Branch")
            commit_btn = gr.Button("💾 Commit")
            push_btn = gr.Button("⬆️ Push", variant="stop")
        
        git_output = gr.Markdown()

    # Event Connections - ALL FIXED for Gradio 4.x+
    create_author_btn.click(
        fn=create_author,
        inputs=[new_author_tb],
        outputs=[author_status, existing_author_dd]
    )

    refresh_btn.click(
        fn=refresh_authors,
        outputs=[existing_author_dd]
    )

    create_article_btn.click(
        fn=create_article,
        inputs=[article_title_tb, existing_author_dd],
        outputs=[article_output]
    )

    # Git buttons
    fork_btn.click(fn=fork_repo, inputs=[pat_tb], outputs=[git_output])
    branch_btn.click(fn=create_branch, inputs=[branch_name_tb, pat_tb], outputs=[git_output])
    commit_btn.click(fn=commit_changes, inputs=[commit_message_tb, pat_tb], outputs=[git_output])
    push_btn.click(fn=push_changes, inputs=[branch_name_tb, pat_tb], outputs=[git_output])

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0", 
        server_port=7860,
        share=False,
        debug=True
    )
