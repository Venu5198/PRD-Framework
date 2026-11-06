import React, { useState, useEffect } from 'react';
import {
  Project,
  AnalysisRecord,
  ClarificationSession,
  PRDVersion,
  PRDSectionContent,
  ValidationReport,
  Job
} from '../types';
import { api } from '../api/client';
import { SectionEditorModal } from '../components/SectionEditorModal';
import { ValidationBadge } from '../components/ValidationBadge';
import {
  ArrowLeft,
  Sparkles,
  HelpCircle,
  FileText,
  CheckCircle2,
  AlertTriangle,
  Download,
  History,
  Layers,
  Upload,
  RefreshCw,
  Edit3,
  ShieldCheck,
  Send,
  Clock,
  Square,
  Loader2
} from 'lucide-react';

interface ProjectViewProps {
  projectId: string;
  onBack: () => void;
}

export const ProjectView: React.FC<ProjectViewProps> = ({ projectId, onBack }) => {
  const [project, setProject] = useState<Project | null>(null);
  const [activeTab, setActiveTab] = useState<'input' | 'analysis' | 'clarifications' | 'prd' | 'requirements' | 'validation' | 'history' | 'export'>('input');
  
  // States
  const [ideaText, setIdeaText] = useState('');
  const [problemText, setProblemText] = useState('');
  const [assignmentText, setAssignmentText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadStatus, setUploadStatus] = useState('');

  const [analysis, setAnalysis] = useState<AnalysisRecord | null>(null);
  const [analyzing, setAnalyzing] = useState(false);

  const [clarifications, setClarifications] = useState<ClarificationSession | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [generatingClarifications, setGeneratingClarifications] = useState(false);

  const [prdVersion, setPrdVersion] = useState<PRDVersion | null>(null);
  const [versionsList, setVersionsList] = useState<PRDVersion[]>([]);
  const [generatingPrd, setGeneratingPrd] = useState(false);

  const [validationReport, setValidationReport] = useState<ValidationReport | null>(null);
  const [validating, setValidating] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [activeJob, setActiveJob] = useState<Job | null>(null);
  const [jobTimer, setJobTimer] = useState<number>(0);

  const [editingSection, setEditingSection] = useState<PRDSectionContent | null>(null);

  // Initial Data Load
  const loadProjectData = async () => {
    try {
      const p = await api.getProject(projectId);
      setProject(p);

      try {
        const an = await api.getAnalysis(projectId);
        setAnalysis(an);
      } catch (_) {}

      try {
        const cl = await api.getClarifications(projectId);
        setClarifications(cl);
      } catch (_) {}

      try {
        const prdRes = await api.getActivePRD(projectId);
        if (prdRes && prdRes.active_version) {
          setPrdVersion(prdRes.active_version);
          setActiveTab('prd'); // jump to PRD if already generated
        }
      } catch (_) {}

      try {
        const vers = await api.getPRDVersions(projectId);
        setVersionsList(vers);
      } catch (_) {}

      try {
        const rep = await api.getValidationReport(projectId);
        if (rep) setValidationReport(rep);
      } catch (_) {}

      // Check for active background PRD generation job
      try {
        const job = await api.getActivePRDJob(projectId);
        if (job) {
          setActiveJob(job);
          if (job.elapsed_seconds) {
            setJobTimer(job.elapsed_seconds);
          }
          if (job.status === 'queued' || job.status === 'running') {
            setActiveTab('prd');
          }
        }
      } catch (_) {}
    } catch (err: any) {
      setErrorMessage(err.message);
    }
  };

  // Background Job Polling Loop
  useEffect(() => {
    let pollInterval: any = null;
    let timerInterval: any = null;

    if (activeJob && (activeJob.status === 'queued' || activeJob.status === 'running')) {
      timerInterval = setInterval(() => {
        setJobTimer((prev) => prev + 1);
      }, 1000);

      pollInterval = setInterval(async () => {
        try {
          const updatedJob = await api.getJob(activeJob.job_id);
          setActiveJob(updatedJob);

          if (updatedJob.status === 'completed') {
            clearInterval(pollInterval);
            clearInterval(timerInterval);
            try {
              const completedPrd = await api.getJobResult(updatedJob.job_id);
              setPrdVersion(completedPrd);
              setActiveTab('prd');
              const vers = await api.getPRDVersions(projectId);
              setVersionsList(vers);
              handleValidatePRD();
            } catch (resErr: any) {
              setErrorMessage(resErr.message);
            }
          } else if (updatedJob.status === 'failed') {
            clearInterval(pollInterval);
            clearInterval(timerInterval);
            setErrorMessage(`AI Generation Failed (${updatedJob.error_code || 'ERROR'}): ${updatedJob.error_message || 'Inference error'}`);
          } else if (updatedJob.status === 'cancelled') {
            clearInterval(pollInterval);
            clearInterval(timerInterval);
          }
        } catch (pollErr: any) {
          console.warn('Error polling job:', pollErr);
        }
      }, 2500);
    }

    return () => {
      if (pollInterval) clearInterval(pollInterval);
      if (timerInterval) clearInterval(timerInterval);
    };
  }, [activeJob?.job_id, activeJob?.status, projectId]);

  useEffect(() => {
    loadProjectData();
  }, [projectId]);

  // 1. Submit Idea
  const handleSubmitIdea = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ideaText.trim()) return;
    setSubmitting(true);
    setErrorMessage(null);
    try {
      await api.submitIdea(
        projectId,
        assignmentText ? 'assignment' : 'idea',
        ideaText,
        problemText,
        assignmentText
      );

      if (selectedFile) {
        await api.uploadReferenceFile(projectId, selectedFile);
        setUploadStatus('File attached successfully.');
      }

      // Automatically trigger analysis
      await handleTriggerAnalysis();
    } catch (err: any) {
      setErrorMessage(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  // 2. Trigger Analysis
  const handleTriggerAnalysis = async () => {
    setAnalyzing(true);
    setErrorMessage(null);
    try {
      const an = await api.analyzeProject(projectId);
      setAnalysis(an);
      setActiveTab('analysis');

      // Auto trigger clarifications
      await handleGenerateClarifications();
    } catch (err: any) {
      setErrorMessage(err.message);
    } finally {
      setAnalyzing(false);
    }
  };

  // 3. Generate Clarifications
  const handleGenerateClarifications = async () => {
    setGeneratingClarifications(true);
    try {
      const cl = await api.generateClarifications(projectId);
      setClarifications(cl);
    } catch (err: any) {
      console.warn(err);
    } finally {
      setGeneratingClarifications(false);
    }
  };

  const handleAnswerQuestion = async (qId: string, proceedWithAssumption: boolean = false) => {
    try {
      const ans = answers[qId];
      await api.answerClarification(projectId, qId, ans, proceedWithAssumption);
      const updatedCl = await api.getClarifications(projectId);
      setClarifications(updatedCl);
    } catch (err: any) {
      setErrorMessage(err.message);
    }
  };

  // 4. Generate Full PRD (Asynchronous Job Submission)
  const handleGeneratePRD = async () => {
    setGeneratingPrd(true);
    setErrorMessage(null);
    try {
      const resp = await api.startPRDGeneration(projectId);
      setJobTimer(0);
      const jobData = await api.getJob(resp.job_id);
      setActiveJob(jobData);
      setActiveTab('prd');
    } catch (err: any) {
      setErrorMessage(err.message);
    } finally {
      setGeneratingPrd(false);
    }
  };

  const handleCancelJob = async () => {
    if (!activeJob) return;
    try {
      await api.cancelJob(activeJob.job_id);
      const updated = await api.getJob(activeJob.job_id);
      setActiveJob(updated);
    } catch (err: any) {
      setErrorMessage(err.message);
    }
  };

  // 5. Validation
  const handleValidatePRD = async (targetVerId?: string) => {
    setValidating(true);
    try {
      const vid = targetVerId || prdVersion?.id;
      const rep = await api.validatePRD(projectId, vid);
      setValidationReport(rep);
    } catch (err: any) {
      console.warn(err);
    } finally {
      setValidating(false);
    }
  };

  // 6. Section Save & Regenerate
  const handleSaveSection = async (secKey: string, content: string, isNa: boolean, naRationale?: string) => {
    const updatedVer = await api.updateSection(projectId, secKey, content, isNa, naRationale);
    setPrdVersion(updatedVer);
    const vers = await api.getPRDVersions(projectId);
    setVersionsList(vers);
    await handleValidatePRD();
  };

  const handleRegenerateSection = async (secKey: string, guidance?: string) => {
    const updatedVer = await api.regenerateSection(projectId, secKey, guidance);
    setPrdVersion(updatedVer);
    const vers = await api.getPRDVersions(projectId);
    setVersionsList(vers);
    await handleValidatePRD();
  };

  // 7. Approve Version
  const handleApproveVersion = async () => {
    if (!prdVersion) return;
    try {
      const approved = await api.approveVersion(projectId, prdVersion.id);
      setPrdVersion(approved);
      const vers = await api.getPRDVersions(projectId);
      setVersionsList(vers);
      alert(`Version ${approved.version_number} has been approved!`);
    } catch (err: any) {
      setErrorMessage(err.message);
    }
  };

  if (!project) {
    return <div className="py-20 text-center text-sm text-slate-500">Loading project data...</div>;
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div className="space-y-1">
          <button
            onClick={onBack}
            className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-500 hover:text-slate-800 transition"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Dashboard</span>
          </button>
          <div className="flex items-center space-x-3">
            <h1 className="text-2xl font-black text-slate-900 tracking-tight">{project.title}</h1>
            <span className="text-xs bg-slate-100 text-slate-700 px-2.5 py-0.5 rounded-full border border-slate-200 font-mono">
              {prdVersion ? prdVersion.version_number : 'Idea Stage'}
            </span>
            {prdVersion?.status === 'approved' && (
              <span className="text-xs bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded font-bold uppercase tracking-wider">
                Approved
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <ValidationBadge report={validationReport} />
          {prdVersion && prdVersion.status !== 'approved' && (
            <button
              onClick={handleApproveVersion}
              className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-lg shadow-sm transition"
            >
              Approve Version
            </button>
          )}
        </div>
      </div>

      {/* Global Error Banner */}
      {errorMessage && (
        <div className="p-4 bg-rose-50 border border-rose-200 text-rose-800 rounded-xl text-sm flex items-center justify-between shadow-sm">
          <div className="flex items-center space-x-2.5">
            <AlertTriangle className="w-5 h-5 text-rose-500 shrink-0" />
            <span className="font-medium">{errorMessage}</span>
          </div>
          <button
            onClick={() => setErrorMessage(null)}
            className="text-xs font-bold text-rose-700 bg-rose-100 hover:bg-rose-200 px-2.5 py-1 rounded transition ml-4 shrink-0"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-200 overflow-x-auto space-x-1 text-sm font-semibold">
        <button
          onClick={() => setActiveTab('input')}
          className={`px-4 py-2.5 border-b-2 whitespace-nowrap flex items-center space-x-2 transition ${
            activeTab === 'input'
              ? 'border-sky-600 text-sky-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Upload className="w-4 h-4" />
          <span>1. Submit Idea</span>
        </button>

        <button
          onClick={() => setActiveTab('analysis')}
          className={`px-4 py-2.5 border-b-2 whitespace-nowrap flex items-center space-x-2 transition ${
            activeTab === 'analysis'
              ? 'border-sky-600 text-sky-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Sparkles className="w-4 h-4" />
          <span>2. AI Analysis</span>
        </button>

        <button
          onClick={() => setActiveTab('clarifications')}
          className={`px-4 py-2.5 border-b-2 whitespace-nowrap flex items-center space-x-2 transition ${
            activeTab === 'clarifications'
              ? 'border-sky-600 text-sky-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <HelpCircle className="w-4 h-4" />
          <span>3. Clarifications</span>
        </button>

        <button
          onClick={() => setActiveTab('prd')}
          className={`px-4 py-2.5 border-b-2 whitespace-nowrap flex items-center space-x-2 transition ${
            activeTab === 'prd'
              ? 'border-sky-600 text-sky-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <FileText className="w-4 h-4" />
          <span>4. PRD Document</span>
        </button>

        <button
          onClick={() => setActiveTab('requirements')}
          className={`px-4 py-2.5 border-b-2 whitespace-nowrap flex items-center space-x-2 transition ${
            activeTab === 'requirements'
              ? 'border-sky-600 text-sky-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Layers className="w-4 h-4" />
          <span>5. Requirements Matrix</span>
        </button>

        <button
          onClick={() => setActiveTab('validation')}
          className={`px-4 py-2.5 border-b-2 whitespace-nowrap flex items-center space-x-2 transition ${
            activeTab === 'validation'
              ? 'border-sky-600 text-sky-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <ShieldCheck className="w-4 h-4" />
          <span>6. Quality Validation</span>
        </button>

        <button
          onClick={() => setActiveTab('history')}
          className={`px-4 py-2.5 border-b-2 whitespace-nowrap flex items-center space-x-2 transition ${
            activeTab === 'history'
              ? 'border-sky-600 text-sky-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <History className="w-4 h-4" />
          <span>7. Versions</span>
        </button>

        <button
          onClick={() => setActiveTab('export')}
          className={`px-4 py-2.5 border-b-2 whitespace-nowrap flex items-center space-x-2 transition ${
            activeTab === 'export'
              ? 'border-sky-600 text-sky-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Download className="w-4 h-4" />
          <span>8. Export</span>
        </button>
      </div>

      {/* Tab 1: Submit Idea */}
      {activeTab === 'input' && (
        <div className="bg-white p-8 rounded-xl border border-slate-200 shadow-sm max-w-4xl mx-auto space-y-6">
          <div className="space-y-1">
            <h2 className="text-xl font-bold text-slate-900">Submit Product Concept or Assignment</h2>
            <p className="text-xs text-slate-500 leading-relaxed">
              Accepts unstructured ideas, problem statements, and academic or client assignments.
              The engine extracts entities, identifies missing info, and structures requirements.
            </p>
          </div>

          <form onSubmit={handleSubmitIdea} className="space-y-5">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                Raw Product Idea / Concept *
              </label>
              <textarea
                required
                rows={5}
                value={ideaText}
                onChange={(e) => setIdeaText(e.target.value)}
                placeholder="Describe what you want to build in plain English (e.g. A desktop application for automated audio transcript indexing with local search and zero cloud tracking)..."
                className="w-full p-3.5 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-sky-500 focus:outline-none"
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Problem Statement (Optional)
                </label>
                <textarea
                  rows={3}
                  value={problemText}
                  onChange={(e) => setProblemText(e.target.value)}
                  placeholder="What friction or limitation do current users face?"
                  className="w-full p-3 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-sky-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Assignment Context / Constraints (Optional)
                </label>
                <textarea
                  rows={3}
                  value={assignmentText}
                  onChange={(e) => setAssignmentText(e.target.value)}
                  placeholder="Paste rubric rules, required sections, or course instructions..."
                  className="w-full p-3 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-sky-500 focus:outline-none"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                Attach Reference Document (PDF, TXT, MD)
              </label>
              <input
                type="file"
                onChange={(e) => setSelectedFile(e.target.files ? e.target.files[0] : null)}
                className="block w-full text-xs text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-sky-50 file:text-sky-700 hover:file:bg-sky-100"
              />
              {uploadStatus && <p className="text-xs text-emerald-600 mt-1">{uploadStatus}</p>}
            </div>

            <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
              <span className="text-xs text-slate-500">
                Operates strictly on your local machine with local AI inference.
              </span>
              <button
                type="submit"
                disabled={submitting || analyzing}
                className="inline-flex items-center space-x-2 px-6 py-2.5 bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold rounded-lg shadow-md transition disabled:opacity-50"
              >
                <Sparkles className="w-4 h-4 text-sky-400" />
                <span>{analyzing ? 'Analyzing Input...' : 'Submit & Analyze Idea'}</span>
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Tab 2: Analysis Results */}
      {activeTab === 'analysis' && (
        <div className="bg-white p-8 rounded-xl border border-slate-200 shadow-sm max-w-4xl mx-auto space-y-6">
          <div className="flex items-center justify-between border-b border-slate-100 pb-4">
            <div>
              <h2 className="text-xl font-bold text-slate-900">AI Input Analysis & Extraction</h2>
              <p className="text-xs text-slate-500">Separation of verified user facts from AI assumptions</p>
            </div>
            <button
              onClick={() => setActiveTab('clarifications')}
              className="px-4 py-2 bg-sky-600 text-white rounded-lg text-xs font-semibold hover:bg-sky-700 transition"
            >
              Proceed to Clarifications →
            </button>
          </div>

          {!analysis ? (
            <div className="py-12 text-center text-slate-400 text-xs">
              No analysis available. Please submit an idea first.
            </div>
          ) : (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
                  <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Product Category</div>
                  <div className="text-base font-bold text-slate-800 mt-1">{analysis.product_category}</div>
                </div>

                <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
                  <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Problem Domain</div>
                  <div className="text-base font-bold text-slate-800 mt-1">{analysis.problem_domain}</div>
                </div>
              </div>

              <div>
                <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-2">Core Objectives</h3>
                <ul className="list-disc list-inside space-y-1 text-xs text-slate-700">
                  {analysis.core_objectives.map((obj, i) => (
                    <li key={i}>{obj}</li>
                  ))}
                </ul>
              </div>

              <div>
                <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-2">Target Users</h3>
                <div className="flex flex-wrap gap-2">
                  {analysis.intended_users.map((u, i) => (
                    <span key={i} className="text-xs bg-slate-100 text-slate-800 px-2.5 py-1 rounded-md font-medium border border-slate-200">
                      {u}
                    </span>
                  ))}
                </div>
              </div>

              {/* Verified Facts vs AI Assumptions Table (FR-015) */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                <div className="p-4 bg-emerald-50/70 border border-emerald-200 rounded-xl space-y-2">
                  <div className="flex items-center space-x-1.5 text-xs font-bold text-emerald-800 uppercase tracking-wider">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    <span>Confirmed User Facts</span>
                  </div>
                  <ul className="text-xs text-emerald-900 space-y-1 list-disc list-inside">
                    {analysis.facts.map((f, i) => (
                      <li key={i}>{f}</li>
                    ))}
                  </ul>
                </div>

                <div className="p-4 bg-amber-50/70 border border-amber-200 rounded-xl space-y-2">
                  <div className="flex items-center space-x-1.5 text-xs font-bold text-amber-800 uppercase tracking-wider">
                    <AlertTriangle className="w-4 h-4 text-amber-600" />
                    <span>AI Engineering Assumptions</span>
                  </div>
                  <ul className="text-xs text-amber-900 space-y-1 list-disc list-inside">
                    {analysis.assumptions.map((a, i) => (
                      <li key={i}>{a}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Clarifications */}
      {activeTab === 'clarifications' && (
        <div className="bg-white p-8 rounded-xl border border-slate-200 shadow-sm max-w-4xl mx-auto space-y-6">
          <div className="flex items-center justify-between border-b border-slate-100 pb-4">
            <div>
              <h2 className="text-xl font-bold text-slate-900">Clarification Engine</h2>
              <p className="text-xs text-slate-500">
                Targeted questions for high-impact ambiguities. You can answer or proceed with documented assumptions.
              </p>
            </div>
            <button
              onClick={handleGeneratePRD}
              disabled={generatingPrd}
              className="inline-flex items-center space-x-2 px-5 py-2 bg-slate-900 text-white rounded-lg text-xs font-bold hover:bg-slate-800 transition disabled:opacity-50"
            >
              <Sparkles className="w-4 h-4 text-sky-400" />
              <span>{generatingPrd ? 'Generating Complete PRD...' : 'Generate 27-Section PRD →'}</span>
            </button>
          </div>

          {!clarifications || clarifications.questions.length === 0 ? (
            <div className="py-12 text-center text-slate-400 text-xs">
              No clarification questions generated yet.
            </div>
          ) : (
            <div className="space-y-5">
              {clarifications.questions.map((q) => (
                <div
                  key={q.id}
                  className="p-5 rounded-xl border border-slate-200 bg-slate-50/50 space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <span className="font-mono text-xs font-bold text-slate-700 bg-white px-2 py-0.5 rounded border border-slate-200">
                        {q.id}
                      </span>
                      <span
                        className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded ${
                          q.priority === 'critical'
                            ? 'bg-rose-100 text-rose-700'
                            : q.priority === 'medium'
                            ? 'bg-amber-100 text-amber-700'
                            : 'bg-sky-100 text-sky-700'
                        }`}
                      >
                        {q.priority}
                      </span>
                      <span className="text-xs text-slate-500 font-medium">Category: {q.category}</span>
                    </div>

                    {q.user_answer ? (
                      <span className="text-xs text-emerald-600 font-semibold flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5" /> Answered
                      </span>
                    ) : q.resolved_as_assumption ? (
                      <span className="text-xs text-amber-600 font-semibold flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5" /> Assumed Default
                      </span>
                    ) : (
                      <span className="text-xs text-slate-400 font-medium">Pending Response</span>
                    )}
                  </div>

                  <p className="text-sm font-semibold text-slate-900">{q.question}</p>
                  <p className="text-xs text-slate-500 italic">Impact: {q.rationale}</p>

                  {/* Suggested Options */}
                  {q.suggested_options.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {q.suggested_options.map((opt, i) => (
                        <button
                          key={i}
                          type="button"
                          onClick={() => {
                            setAnswers({ ...answers, [q.id]: opt });
                          }}
                          className="text-[11px] bg-white border border-slate-300 hover:border-sky-500 px-2.5 py-1 rounded text-slate-700 transition"
                        >
                          + {opt}
                        </button>
                      ))}
                    </div>
                  )}

                  {/* Answer Input */}
                  <div className="flex gap-2 pt-1">
                    <input
                      type="text"
                      placeholder="Type your answer or click a suggested option above..."
                      value={answers[q.id] || q.user_answer || ''}
                      onChange={(e) => setAnswers({ ...answers, [q.id]: e.target.value })}
                      className="flex-1 px-3 py-1.5 border border-slate-300 rounded-md text-xs focus:ring-2 focus:ring-sky-500 bg-white"
                    />
                    <button
                      type="button"
                      onClick={() => handleAnswerQuestion(q.id, false)}
                      className="px-3 py-1.5 bg-sky-600 hover:bg-sky-700 text-white text-xs font-semibold rounded-md transition"
                    >
                      Save Answer
                    </button>
                    <button
                      type="button"
                      onClick={() => handleAnswerQuestion(q.id, true)}
                      title="Skip and let engine document this as an explicit assumption"
                      className="px-3 py-1.5 bg-slate-200 hover:bg-slate-300 text-slate-700 text-xs font-medium rounded-md transition"
                    >
                      Accept Assumption
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 4: PRD Document Viewer & Editor */}
      {activeTab === 'prd' && (
        <div className="space-y-6">
          {!prdVersion ? (
            activeJob && (activeJob.status === 'queued' || activeJob.status === 'running') ? (
              <div className="bg-white p-8 rounded-xl border border-sky-200 shadow-sm max-w-2xl mx-auto space-y-6">
                <div className="flex items-center justify-between border-b border-slate-100 pb-4">
                  <div className="flex items-center space-x-3">
                    <div className="p-2 bg-sky-50 text-sky-600 rounded-lg">
                      <RefreshCw className="w-5 h-5 animate-spin" />
                    </div>
                    <div>
                      <h3 className="text-base font-bold text-slate-900">
                        {activeJob.status === 'queued' ? 'Job Queued in Background' : 'AI PRD Synthesis in Progress'}
                      </h3>
                      <p className="text-xs text-slate-500">
                        Model: <span className="font-semibold">{activeJob.model}</span> ({activeJob.provider}) | Job ID: <span className="font-mono">{activeJob.job_id.slice(0, 8)}...</span>
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="inline-flex items-center space-x-1 px-2.5 py-1 bg-amber-50 text-amber-800 text-xs font-mono font-medium rounded-full">
                      <Clock className="w-3.5 h-3.5" />
                      <span>{Math.floor(jobTimer / 60)}m {String(jobTimer % 60).padStart(2, '0')}s</span>
                    </span>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="space-y-2">
                  <div className="flex justify-between text-xs font-semibold text-slate-700">
                    <span>{activeJob.progress_metadata?.stage_name || 'Processing...'}</span>
                    <span>Stage {(activeJob.progress_metadata?.step || 1)} of {activeJob.total_stages}</span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-sky-600 h-2 rounded-full transition-all duration-500 ease-out"
                      style={{ width: `${Math.max(8, Math.round((activeJob.completed_stages.length / activeJob.total_stages) * 100))}%` }}
                    />
                  </div>
                </div>

                {/* Stage Checklist */}
                <div className="bg-slate-50 p-4 rounded-lg border border-slate-200/60 space-y-2">
                  <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-2">Sequential AI Pipeline Stages</p>
                  {[
                    { key: 'input_analysis', label: '1. Input Analysis & Context Extraction' },
                    { key: 'requirements_engineering', label: '2. Functional & Non-Functional Requirements' },
                    { key: 'stakeholder_analysis', label: '3. Stakeholder & Persona Analysis' },
                    { key: 'business_rules', label: '4. Business Rules Extraction' },
                    { key: 'risk_analysis', label: '5. Risk & Mitigation Engineering' },
                    { key: 'prd_assembly', label: '6. Canonical 27-Section Synthesis' },
                  ].map((stage) => {
                    const isCompleted = activeJob.completed_stages.includes(stage.key);
                    const isCurrent = activeJob.current_stage === stage.key;
                    return (
                      <div key={stage.key} className="flex items-center justify-between text-xs py-1">
                        <span className={`flex items-center space-x-2 ${isCompleted ? 'text-emerald-700 font-medium' : isCurrent ? 'text-sky-700 font-bold' : 'text-slate-400'}`}>
                          {isCompleted ? (
                            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                          ) : isCurrent ? (
                            <RefreshCw className="w-4 h-4 text-sky-600 animate-spin" />
                          ) : (
                            <div className="w-4 h-4 rounded-full border border-slate-300" />
                          )}
                          <span>{stage.label}</span>
                        </span>
                        <span className="text-[10px] font-mono">
                          {isCompleted ? 'DONE' : isCurrent ? 'IN PROGRESS' : 'WAITING'}
                        </span>
                      </div>
                    );
                  })}
                </div>

                <div className="flex justify-between items-center pt-2">
                  <p className="text-[11px] text-slate-400">
                    Runs persistently on your local machine. You can refresh or leave this tab safely.
                  </p>
                  <button
                    onClick={handleCancelJob}
                    className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-50 rounded-lg transition"
                  >
                    <Square className="w-3.5 h-3.5" />
                    <span>Cancel Generation</span>
                  </button>
                </div>
              </div>
            ) : activeJob && activeJob.status === 'failed' ? (
              <div className="bg-white p-8 text-center rounded-xl border border-rose-200 max-w-xl mx-auto space-y-4 shadow-sm">
                <AlertTriangle className="w-12 h-12 text-rose-500 mx-auto" />
                <div>
                  <h3 className="text-base font-bold text-slate-900">PRD Generation Failed</h3>
                  <p className="text-xs text-rose-600 font-mono mt-1 bg-rose-50 p-2 rounded">
                    {activeJob.error_code}: {activeJob.error_message || 'Inference error occurred'}
                  </p>
                </div>
                <button
                  onClick={handleGeneratePRD}
                  className="px-5 py-2.5 bg-slate-900 text-white rounded-lg text-xs font-bold hover:bg-slate-800 transition"
                >
                  Retry PRD Generation
                </button>
              </div>
            ) : (
              <div className="bg-white p-12 text-center rounded-xl border border-slate-200 max-w-xl mx-auto space-y-4">
                <FileText className="w-12 h-12 text-slate-300 mx-auto" />
                <div>
                  <h3 className="text-base font-bold text-slate-900">PRD Document Not Generated Yet</h3>
                  <p className="text-xs text-slate-500 mt-1">
                    Complete the clarification stage or click below to synthesize all 27 canonical sections.
                  </p>
                </div>
                <button
                  onClick={handleGeneratePRD}
                  disabled={generatingPrd}
                  className="px-5 py-2.5 bg-slate-900 text-white rounded-lg text-xs font-bold hover:bg-slate-800 transition"
                >
                  {generatingPrd ? 'Generating Complete PRD...' : 'Generate PRD Now'}
                </button>
              </div>
            )
          ) : (
            <div className="space-y-6">
              {/* Document Banner */}
              <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center space-x-2">
                    <h2 className="text-lg font-bold text-slate-900">Canonical 27-Section PRD Specification</h2>
                    <span className="text-xs bg-sky-100 text-sky-800 px-2 py-0.5 rounded font-mono font-bold">
                      {prdVersion.version_number}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Changelog: {prdVersion.changelog} | Created {new Date(prdVersion.created_at).toLocaleString()}
                  </p>
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => handleValidatePRD()}
                    disabled={validating}
                    className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-semibold rounded-lg transition"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${validating ? 'animate-spin' : ''}`} />
                    <span>Run Validation</span>
                  </button>
                  <button
                    onClick={() => setActiveTab('export')}
                    className="inline-flex items-center space-x-1.5 px-4 py-1.5 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-lg transition shadow-sm"
                  >
                    <Download className="w-3.5 h-3.5 text-sky-400" />
                    <span>Export Document</span>
                  </button>
                </div>
              </div>

              {/* Sections Accordion / Cards */}
              <div className="space-y-4">
                {Object.values(prdVersion.sections).map((sec) => (
                  <div
                    key={sec.key}
                    className="bg-white rounded-xl border border-slate-200 shadow-sm hover:border-slate-300 transition overflow-hidden"
                  >
                    <div className="flex items-center justify-between px-6 py-4 bg-slate-50/70 border-b border-slate-100">
                      <div className="flex items-center space-x-3">
                        <span className="font-bold text-sm text-slate-900">{sec.title}</span>
                        {sec.is_na && (
                          <span className="text-[10px] bg-slate-200 text-slate-600 px-2 py-0.5 rounded font-bold uppercase">
                            Not Applicable
                          </span>
                        )}
                      </div>
                      <button
                        onClick={() => setEditingSection(sec)}
                        className="inline-flex items-center space-x-1 text-xs font-semibold text-sky-600 hover:text-sky-800 hover:bg-sky-50 px-2.5 py-1 rounded-md transition"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                        <span>Edit / Regenerate</span>
                      </button>
                    </div>

                    <div className="p-6">
                      {sec.is_na ? (
                        <p className="text-xs text-slate-400 italic">
                          Marked as Not Applicable: {sec.na_rationale || 'Omitted from scope'}
                        </p>
                      ) : (
                        <div className="prose prose-sm max-w-none text-slate-800 text-xs leading-relaxed whitespace-pre-wrap font-sans">
                          {sec.content}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 5: Requirements Matrix */}
      {activeTab === 'requirements' && (
        <div className="bg-white p-8 rounded-xl border border-slate-200 shadow-sm space-y-6">
          <div>
            <h2 className="text-xl font-bold text-slate-900">Requirements & Traceability Matrix</h2>
            <p className="text-xs text-slate-500">
              Stable identifiers for Functional Requirements (FR), Non-Functional Requirements (NFR),
              Business Rules (BR), and Acceptance Criteria (AC).
            </p>
          </div>

          {prdVersion?.sections['functional_requirements'] ? (
            <div className="space-y-6">
              <div>
                <h3 className="text-sm font-bold text-slate-800 mb-2">Functional Requirements</h3>
                <div className="overflow-x-auto border border-slate-200 rounded-lg p-4 bg-slate-50/50 text-xs whitespace-pre-wrap font-mono">
                  {prdVersion.sections['functional_requirements'].content}
                </div>
              </div>

              <div>
                <h3 className="text-sm font-bold text-slate-800 mb-2">Acceptance Criteria</h3>
                <div className="overflow-x-auto border border-slate-200 rounded-lg p-4 bg-slate-50/50 text-xs whitespace-pre-wrap font-mono">
                  {prdVersion.sections['acceptance_criteria']?.content}
                </div>
              </div>

              <div>
                <h3 className="text-sm font-bold text-slate-800 mb-2">Business Rules</h3>
                <div className="overflow-x-auto border border-slate-200 rounded-lg p-4 bg-slate-50/50 text-xs whitespace-pre-wrap font-mono">
                  {prdVersion.sections['business_rules']?.content}
                </div>
              </div>
            </div>
          ) : (
            <p className="text-xs text-slate-400 py-8 text-center">PRD not generated yet.</p>
          )}
        </div>
      )}

      {/* Tab 6: Quality Validation */}
      {activeTab === 'validation' && (
        <div className="bg-white p-8 rounded-xl border border-slate-200 shadow-sm space-y-6">
          <div className="flex items-center justify-between border-b border-slate-100 pb-4">
            <div>
              <h2 className="text-xl font-bold text-slate-900">Deterministic Quality & Validation Suite</h2>
              <p className="text-xs text-slate-500">
                Automated structural completeness, ID collision detection, duplicate removal, and acceptance criteria coverage.
              </p>
            </div>
            <button
              onClick={() => handleValidatePRD()}
              disabled={validating}
              className="px-4 py-2 bg-slate-900 text-white rounded-lg text-xs font-semibold hover:bg-slate-800 transition"
            >
              {validating ? 'Running Suite...' : 'Re-Run Validation'}
            </button>
          </div>

          {!validationReport ? (
            <div className="py-12 text-center text-slate-400 text-xs">
              Validation report pending. Click 'Re-Run Validation' above.
            </div>
          ) : (
            <div className="space-y-6">
              <div className="p-5 rounded-xl border border-slate-200 bg-slate-50 flex items-center justify-between">
                <div>
                  <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">Quality Score</div>
                  <div className="text-3xl font-black text-slate-900">{validationReport.score} / 100</div>
                </div>
                <div className="flex gap-4 text-xs font-semibold">
                  <div className="text-rose-600 bg-rose-50 px-3 py-1.5 rounded-lg border border-rose-200">
                    {validationReport.error_count} Blocking Errors
                  </div>
                  <div className="text-amber-600 bg-amber-50 px-3 py-1.5 rounded-lg border border-amber-200">
                    {validationReport.warning_count} Warnings
                  </div>
                  <div className="text-sky-600 bg-sky-50 px-3 py-1.5 rounded-lg border border-sky-200">
                    {validationReport.info_count} Style Suggestions
                  </div>
                </div>
              </div>

              <div className="space-y-3">
                <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                  Validation Findings ({validationReport.issues.length})
                </h3>
                {validationReport.issues.length === 0 ? (
                  <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-800 font-medium">
                    All quality gates passed! Zero errors and zero unmapped requirements detected.
                  </div>
                ) : (
                  validationReport.issues.map((iss, i) => (
                    <div
                      key={i}
                      className={`p-4 rounded-lg border text-xs space-y-1.5 ${
                        iss.severity === 'error'
                          ? 'bg-rose-50/60 border-rose-200 text-rose-900'
                          : iss.severity === 'warning'
                          ? 'bg-amber-50/60 border-amber-200 text-amber-900'
                          : 'bg-slate-50 border-slate-200 text-slate-800'
                      }`}
                    >
                      <div className="flex items-center space-x-2 font-bold">
                        <span className="font-mono">{iss.rule_id}</span>
                        <span>•</span>
                        <span>{iss.title}</span>
                      </div>
                      <p className="text-slate-600">{iss.description}</p>
                      <p className="text-slate-700 font-medium">
                        <strong>Recommendation:</strong> {iss.recommendation}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 7: Version History */}
      {activeTab === 'history' && (
        <div className="bg-white p-8 rounded-xl border border-slate-200 shadow-sm space-y-6">
          <div>
            <h2 className="text-xl font-bold text-slate-900">Document Version History</h2>
            <p className="text-xs text-slate-500">
              PRD versions are immutable. Section edits and regenerations produce incremental snapshots.
            </p>
          </div>

          <div className="space-y-3">
            {versionsList.map((ver) => (
              <div
                key={ver.id}
                className="p-4 rounded-xl border border-slate-200 hover:border-slate-300 flex items-center justify-between"
              >
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="font-bold text-sm text-slate-900">{ver.version_number}</span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                        ver.status === 'approved'
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-slate-100 text-slate-700'
                      }`}
                    >
                      {ver.status}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500">
                    {ver.changelog} • {new Date(ver.created_at).toLocaleString()}
                  </p>
                </div>

                <button
                  onClick={async () => {
                    setPrdVersion(ver);
                    setActiveTab('prd');
                    try {
                      const rep = await api.getValidationReport(projectId, ver.id);
                      if (rep) {
                        setValidationReport(rep);
                      } else {
                        const newRep = await api.validatePRD(projectId, ver.id);
                        setValidationReport(newRep);
                      }
                    } catch (_) {}
                  }}
                  className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-md transition"
                >
                  View Snapshot
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 8: Export Center */}
      {activeTab === 'export' && (
        <div className="bg-white p-8 rounded-xl border border-slate-200 shadow-sm max-w-3xl mx-auto space-y-6">
          <div className="text-center space-y-2">
            <h2 className="text-xl font-bold text-slate-900">PRD Export Center</h2>
            <p className="text-xs text-slate-500 max-w-md mx-auto">
              Export validated requirements in industry standard formats with full tables,
              headers, and acceptance criteria preserved.
            </p>
            {prdVersion && (
              <p className="text-xs font-semibold text-slate-700 pt-1">
                Currently Selected Version:{' '}
                <span className="px-2 py-0.5 bg-indigo-50 text-indigo-700 border border-indigo-200 rounded font-bold">
                  {prdVersion.version_number}
                </span>{' '}
                <span className="text-slate-400 font-normal">({prdVersion.id})</span>
              </p>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4">
            <a
              href={api.getExportUrl(projectId, 'markdown', prdVersion?.id)}
              download
              className="p-6 rounded-xl border-2 border-slate-200 hover:border-sky-500 hover:shadow-md transition text-center space-y-3 block bg-slate-50/50"
            >
              <div className="w-12 h-12 bg-sky-100 text-sky-700 rounded-full flex items-center justify-center mx-auto">
                <FileText className="w-6 h-6" />
              </div>
              <h3 className="font-bold text-sm text-slate-900">Markdown (.md)</h3>
              <p className="text-[11px] text-slate-500">
                GitHub-flavored Markdown format with tables and code fences.
              </p>
              <span className="inline-block text-xs font-bold text-sky-600 mt-2">
                Download .MD ↓
              </span>
            </a>

            <a
              href={api.getExportUrl(projectId, 'docx', prdVersion?.id)}
              download
              className="p-6 rounded-xl border-2 border-slate-200 hover:border-blue-500 hover:shadow-md transition text-center space-y-3 block bg-slate-50/50"
            >
              <div className="w-12 h-12 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center mx-auto">
                <FileText className="w-6 h-6" />
              </div>
              <h3 className="font-bold text-sm text-slate-900">Microsoft Word (.docx)</h3>
              <p className="text-[11px] text-slate-500">
                Professional Office OpenXML document with formatted tables and titles.
              </p>
              <span className="inline-block text-xs font-bold text-blue-600 mt-2">
                Download .DOCX ↓
              </span>
            </a>

            <a
              href={api.getExportUrl(projectId, 'pdf', prdVersion?.id)}
              download
              className="p-6 rounded-xl border-2 border-slate-200 hover:border-rose-500 hover:shadow-md transition text-center space-y-3 block bg-slate-50/50"
            >
              <div className="w-12 h-12 bg-rose-100 text-rose-700 rounded-full flex items-center justify-center mx-auto">
                <FileText className="w-6 h-6" />
              </div>
              <h3 className="font-bold text-sm text-slate-900">Adobe PDF (.pdf)</h3>
              <p className="text-[11px] text-slate-500">
                Print-ready PDF report with numbered headings and headers.
              </p>
              <span className="inline-block text-xs font-bold text-rose-600 mt-2">
                Download .PDF ↓
              </span>
            </a>
          </div>
        </div>
      )}

      {/* Section Edit Modal */}
      {editingSection && (
        <SectionEditorModal
          section={editingSection}
          isOpen={true}
          onClose={() => setEditingSection(null)}
          onSave={handleSaveSection}
          onRegenerate={handleRegenerateSection}
        />
      )}
    </div>
  );
};

