import React, { useEffect } from 'react';
import { Routes, Route, useLocation } from 'react-router-dom';

import './css/style.css';
import './charts/ChartjsConfig';

// Original pages
import Dashboard from './pages/Dashboard';
import PatientList from './pages/PatientList';
import PatientDetail from './pages/PatientDetail';
import SlideAnalysis from './pages/SlideAnalysis';
import PatientTimeline from './pages/PatientTimeline';
import DigitalTwin from './pages/DigitalTwin';
import TreatmentComparison from './pages/TreatmentComparison';
import UncertaintyView from './pages/UncertaintyView';
import CohortAnalytics from './pages/CohortAnalytics';
import BiomarkerExplorer from './pages/BiomarkerExplorer';
import KnowledgeGraphView from './pages/KnowledgeGraphView';
import FederatedStatus from './pages/FederatedStatus';
import ReportGenerator from './pages/ReportGenerator';
import Settings from './pages/Settings';

// Wow-factor pages
import CommandCenter from './pages/CommandCenter';
import TumorMicroenvironment from './pages/TumorMicroenvironment';
import GenomicConstellation from './pages/GenomicConstellation';
import ClinicalWorkflow from './pages/ClinicalWorkflow';
import MultiOmicsHub from './pages/MultiOmicsHub';

// Advanced deep learning pages
import Reconstruction3D from './pages/Reconstruction3D';
import VirtualStaining from './pages/VirtualStaining';
import CellGraphNetwork from './pages/CellGraphNetwork';
import SurvivalPrediction from './pages/SurvivalPrediction';
import AttentionHeatmaps from './pages/AttentionHeatmaps';

// CV & substance pages
import PatientWellness from './pages/PatientWellness';
import RehabTracker from './pages/RehabTracker';
import SpatialTranscriptomics from './pages/SpatialTranscriptomics';
import TrialMatcher from './pages/TrialMatcher';
import TumorBoard from './pages/TumorBoard';
import DrugMechanisms from './pages/DrugMechanisms';
import NCCNNavigator from './pages/NCCNNavigator';
import PathologyLab from './pages/PathologyLab';
import PopulationHealth from './pages/PopulationHealth';

function App() {
  const location = useLocation();

  useEffect(() => {
    document.querySelector('html').style.scrollBehavior = 'auto';
    window.scroll({ top: 0 });
    document.querySelector('html').style.scrollBehavior = '';
  }, [location.pathname]);

  return (
    <Routes>
      <Route exact path="/" element={<Dashboard />} />
      <Route path="/patients" element={<PatientList />} />
      <Route path="/patients/:id" element={<PatientDetail />} />
      <Route path="/patients/:id/timeline" element={<PatientTimeline />} />
      <Route path="/slide-analysis" element={<SlideAnalysis />} />
      <Route path="/digital-twin" element={<DigitalTwin />} />
      <Route path="/digital-twin/:id" element={<DigitalTwin />} />
      <Route path="/treatment-comparison" element={<TreatmentComparison />} />
      <Route path="/treatment-comparison/:id" element={<TreatmentComparison />} />
      <Route path="/uncertainty" element={<UncertaintyView />} />
      <Route path="/cohort" element={<CohortAnalytics />} />
      <Route path="/biomarkers" element={<BiomarkerExplorer />} />
      <Route path="/knowledge-graph" element={<KnowledgeGraphView />} />
      <Route path="/federated" element={<FederatedStatus />} />
      <Route path="/reports" element={<ReportGenerator />} />
      <Route path="/reports/:id" element={<ReportGenerator />} />
      <Route path="/settings" element={<Settings />} />

      {/* Wow-factor pages */}
      <Route path="/command-center" element={<CommandCenter />} />
      <Route path="/tumor-microenvironment" element={<TumorMicroenvironment />} />
      <Route path="/genomic-constellation" element={<GenomicConstellation />} />
      <Route path="/clinical-workflow" element={<ClinicalWorkflow />} />
      <Route path="/multi-omics" element={<MultiOmicsHub />} />

      {/* Advanced deep learning pages */}
      <Route path="/3d-reconstruction" element={<Reconstruction3D />} />
      <Route path="/virtual-staining" element={<VirtualStaining />} />
      <Route path="/cell-graph" element={<CellGraphNetwork />} />
      <Route path="/survival-prediction" element={<SurvivalPrediction />} />
      <Route path="/attention-heatmaps" element={<AttentionHeatmaps />} />

      {/* CV & substance pages */}
      <Route path="/patient-wellness" element={<PatientWellness />} />
      <Route path="/rehab-tracker" element={<RehabTracker />} />
      <Route path="/spatial-transcriptomics" element={<SpatialTranscriptomics />} />
      <Route path="/trial-matcher" element={<TrialMatcher />} />
      <Route path="/tumor-board" element={<TumorBoard />} />
      <Route path="/drug-mechanisms" element={<DrugMechanisms />} />
      <Route path="/guideline-navigator" element={<NCCNNavigator />} />
      <Route path="/pathology-lab" element={<PathologyLab />} />
      <Route path="/population-health" element={<PopulationHealth />} />
    </Routes>
  );
}

export default App;
