\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{gh}[2026/10/26 Template documenti Git Happens]
\LoadClass[11pt,a4paper]{article}

% --- PACCHETTI PRINCIPALI ---
\RequirePackage[utf8]{inputenc}
\RequirePackage[T1]{fontenc}
\RequirePackage[italian]{babel}
\RequirePackage[margin=2.5cm, headheight=20pt, footskip=33pt]{geometry}
\RequirePackage{graphicx}
\RequirePackage{tabularx}
\RequirePackage{booktabs}
\RequirePackage{fancyhdr}
\RequirePackage{hyperref}
\RequirePackage{xcolor}
\RequirePackage{tikz}
\RequirePackage{xspace}

% --- CONFIGURAZIONE COLORI E LINK ---
\definecolor{primaryDark}{HTML}{2B2D42}
\hypersetup{
    colorlinks=true,
    linkcolor=black,
    urlcolor=blue
}

% --- DATI DEL DOCUMENTO (da impostare in main.tex) ---
\newcommand{\tipodoc}[1]{\renewcommand{\documento}{#1\xspace}}
\newcommand{\documento}{Documento\xspace}
\newcommand{\datadoc}[1]{\renewcommand{\@datadoc}{#1}}
\newcommand{\modalita}[1]{\renewcommand{\@modalita}{#1}}
\newcommand{\orario}[1]{\renewcommand{\@orario}{#1}}
\newcommand{\redattori}[1]{\renewcommand{\@redattori}{#1}}
\newcommand{\verificatori}[1]{\renewcommand{\@verificatori}{#1}}
\newcommand{\amministratore}[1]{\renewcommand{\@amministratore}{#1}}
\newcommand{\responsabile}[1]{\renewcommand{\@responsabile}{#1}}
\newcommand{\destinatari}[1]{\renewcommand{\@destinatari}{#1}}
\makeatletter
\newcommand{\@datadoc}{}
\newcommand{\@modalita}{}
\newcommand{\@orario}{}
\newcommand{\@redattori}{}
\newcommand{\@verificatori}{}
\newcommand{\@amministratore}{}
\newcommand{\@responsabile}{}
\newcommand{\@destinatari}{}
\makeatother

% Elenco su piu' righe dentro una cella: \lista{A. Rossi \\ B. Bianchi}
\newcommand{\lista}[1]{\begin{tabular}[t]{@{}l@{}}#1\end{tabular}}

% Campi opzionali: la riga (o la data) compare solo se il campo e' stato impostato
\makeatletter
\newcommand{\inforow}[2]{%
    \ifx#2\@empty\else\textbf{#1} & \lista{#2} \\\fi}
\newcommand{\@ifdatadoc}[1]{\ifx\@datadoc\@empty\else#1\fi}
\makeatother

% --- STILE PIÈ DI PAGINA ---
\pagestyle{fancy}
\fancyhf{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0.4pt}

\fancyfoot[C]{%
    \vspace{0.15cm}%
    \noindent
    \begin{minipage}[c]{0.12\textwidth}
        \includegraphics[height=50pt,keepaspectratio]{LogoSmallNoBg.png}
    \end{minipage}%
    \begin{minipage}[c]{0.48\textwidth}
    \footnotesize \textcolor{gray}{Git Happens} \quad \footnotesize \documento
    \end{minipage}%
    \begin{minipage}[c]{0.40\textwidth}
        \raggedleft
        \footnotesize  \quad {\small \thepage}
    \end{minipage}%
}

% --- PRIMA PAGINA: INTESTAZIONE E INFORMAZIONI ---
\makeatletter
\newcommand{\makeheader}{%
\thispagestyle{empty}
\begin{center}
    \includegraphics[width=10cm]{LogoNoBg.png}\\[0.4cm]
    {\large \textbf{Git Happens}}\\[0.2cm]
    {\small \texttt{githappens4swe@gmail.com}}\\[0.6cm]
    {\Large \textbf{\documento \@ifdatadoc{\quad Data: \@datadoc}}}
\end{center}

\vspace{0.8cm}

\noindent{\large \textbf{Informazioni documento}}\\[0.3cm]
\renewcommand{\arraystretch}{1.4}
\noindent\begin{tabularx}{\textwidth}{@{} p{3.8cm} X @{}}
    \inforow{Modalità}{\@modalita}
    \inforow{Orario}{\@orario}
    \inforow{Redattori}{\@redattori}
    \inforow{Verificatori}{\@verificatori}
    \inforow{Amministratore}{\@amministratore}
    \inforow{Responsabile}{\@responsabile}
    \inforow{Destinatari}{\@destinatari}
\end{tabularx}

\vfill

\noindent\rule{\textwidth}{0.4pt}\\[0.15cm]
\noindent
\begin{minipage}[c]{0.12\textwidth}
    \includegraphics[height=50pt,keepaspectratio]{LogoSmallNoBg.png}
\end{minipage}%
\begin{minipage}[c]{0.48\textwidth}
    \footnotesize \quad \documento
\end{minipage}%
\begin{minipage}[c]{0.40\textwidth}
    \raggedleft
    \footnotesize \ifx\@responsabile\@empty\else Il responsabile: \@responsabile \quad \fi {\small 1}
\end{minipage}
\newpage
}
\makeatother
