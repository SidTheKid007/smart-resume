from flask import Flask, render_template, request, send_file
from openai import OpenAI
import pdfkit
import os
from datetime import datetime
import re

app = Flask(__name__)

api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        user_resume = request.form.get("user_resume")
        job_desc = request.form.get("job_desc")

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert resume writer."},
                {"role": "user", "content": f"Here is my resume:\n{user_resume}\n\n"
                                             f"And here is the job description:\n{job_desc}\n\n"
                                             "Please create a tailored resume that combines my experience with the job requirements."}
            ]
        )
        tailored_resume = response.choices[0].message.content

        tailored_resume = re.sub(r"^.*?(?=\n)", "", tailored_resume, flags=re.DOTALL)
        tailored_resume = re.sub(r"(Make sure.*|This resume.*|Remember.*|This tailored.*|This version.*|It highlights.*|Ensure.*|Tailor.*)", "", tailored_resume, flags=re.IGNORECASE | re.DOTALL).strip()
        tailored_resume = clean_unicode_garbage(tailored_resume)
        tailored_resume = convert_markdown_links(tailored_resume)

        formatted_resume_html = format_resume_text(tailored_resume)

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: 'Helvetica Neue', sans-serif;
                    padding: 20px;
                    line-height: 1.4;
                    color: #333;
                }}
                h1 {{
                    text-align: center;
                    color: #4a90e2;
                    font-size: 36px;
                    margin-bottom: 10px;
                }}
                h2 {{
                    color: #4a90e2;
                    border-bottom: 1px solid #4a90e2;
                    padding-bottom: 5px;
                    margin-top: 25px;
                }}
                ul {{
                    color: #4a90e2;
                    margin: 0 0 15px 20px;
                    padding: 0;
                }}
                li {{
                    margin-bottom: 5px;
                    color: #333;
                }}
                p {{
                    margin: 0 0 10px 0;
                }}
            </style>
        </head>
        <body>
            <h1>Resume</h1>
            {formatted_resume_html}
        </body>
        </html>
        """
        pdf_path = f"generated_resumes/resume_{timestamp}.pdf"
        pdfkit.from_string(html_content, pdf_path, options={'encoding': "UTF-8"})

        return render_template("index.html", pdf_file=pdf_path.split("/")[-1], preview_text=tailored_resume, user_resume=user_resume)

    return render_template("index.html")

@app.route("/download/<filename>")
def download_file(filename):
    path = f"generated_resumes/{filename}"
    return send_file(path, as_attachment=True)

def convert_markdown_links(text):
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)

def clean_unicode_garbage(text):
    replacements = {
        "â€“": "-",
        "â€”": "-",
        "â€˜": "'",
        "â€™": "'",
        "â€œ": '"',
        "â€": '"',
        "â€": '"',
        "Â": "",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    return text

def clean_line(line):
    line = line.strip()
    if line.startswith("<h2>") and line.endswith("</h2>"):
        content = line[4:-5].strip()
        content = re.sub(r"^[-:]+", "", content).strip()
        content = re.sub(r"[-:]+$", "", content).strip()
        if not content:
            return ""  
        return f"<h2>{content}</h2>"
    line = re.sub(r"^[-:]+", "", line).strip()
    line = re.sub(r"[-:]+$", "", line).strip()
    return line



def format_resume_text(raw_text):
    formatted = re.sub(r"\*\*(.*?)\*\*", r"<h2>\1</h2>", raw_text)
    formatted = re.sub(r"\*(.*?)\*", r"<em>\1</em>", formatted)
    formatted = formatted.replace('---', '')

    lines = formatted.splitlines()
    final_lines = []
    inside_list = False

    for line in lines:
        stripped_line = line.strip()
        if stripped_line in ["-", "*", "- ", "* "]:
            continue 

        cleaned_line = clean_line(stripped_line)
        if not cleaned_line or cleaned_line in ["-", "*"]:
            continue

        if "<h2>" in cleaned_line:
            if inside_list:
                final_lines.append("</ul>")
                inside_list = False
            final_lines.append(cleaned_line)
        elif stripped_line.startswith("- "):
            cleaned_bullet = clean_line(stripped_line[2:])
            if not inside_list:
                final_lines.append("<ul>")
                inside_list = True
            final_lines.append(f"<li>{cleaned_bullet}</li>")
        else:
            if inside_list:
                final_lines.append("</ul>")
                inside_list = False
            final_lines.append(f"<p>{cleaned_line}</p>")

    if inside_list:
        final_lines.append("</ul>")
    return "\n".join(final_lines)

if __name__ == "__main__":
    app.run(debug=True)
