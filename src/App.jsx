import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar/Navbar';
import { Hero } from './components/Hero/Hero';
import { DashboardTeaser } from './components/DashboardEmbed/DashboardTeaser';
import { OperationsApp } from './components/ConsoleApp/OperationsApp';
import { HowItWorks } from './components/Features/HowItWorks';
import { ImpactCalculatorSection } from './components/Calculator/ImpactCalculatorSection';
import { ComparisonSection } from './components/Comparison/ComparisonSection';
import { Footer } from './components/Footer/Footer';
import { RequestDemoModal } from './components/DemoModal/RequestDemoModal';
import { LogSurplusModal } from './components/SurplusModal/LogSurplusModal';
import { ToastContainer } from './components/Toast/ToastContainer';

import {
  INITIAL_WEATHER,
  FOOD_BANKS_AND_HUBS,
  DONORS,
  RECIPIENTS,
  INITIAL_FLEET,
  INITIAL_MATCH_RECOMMENDATIONS,
  PERISHABILITY_CATEGORIES,
  DISTRICT_DEMAND_FORECAST,
  AI_INTEGRATION_ENDPOINTS
} from './data/mockData';

export function App() {
  // Page Route State ('landing' | 'console')
  const [currentRoute, setCurrentRoute] = useState(
    window.location.hash.includes('console') || window.location.pathname === '/console' ? 'console' : 'landing'
  );

  useEffect(() => {
    const handleHashChange = () => {
      if (window.location.hash.includes('console') || window.location.pathname === '/console') {
        setCurrentRoute('console');
      } else {
        setCurrentRoute('landing');
      }
    };
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const navigateToConsole = () => {
    window.location.hash = 'console';
    setCurrentRoute('console');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const navigateToLanding = () => {
    window.location.hash = '';
    setCurrentRoute('landing');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Operational Simulation state
  const [activeScenario, setActiveScenario] = useState('baseline');
  
  // Data state
  const [weather, setWeather] = useState(INITIAL_WEATHER);
  const [donors, setDonors] = useState(DONORS);
  const [hubs, setHubs] = useState(FOOD_BANKS_AND_HUBS);
  const [recipients, setRecipients] = useState(RECIPIENTS);
  const [fleet, setFleet] = useState(INITIAL_FLEET);
  const [matches, setMatches] = useState(INITIAL_MATCH_RECOMMENDATIONS);
  const [categories, setCategories] = useState(PERISHABILITY_CATEGORIES);
  const [districts, setDistricts] = useState(DISTRICT_DEMAND_FORECAST);

  // Operational KPI stats
  const [stats, setStats] = useState({
    rescuedLbs: 14600,
    rescuedChangePct: 22.4,
    spoilagePreventionRate: 98.2,
    activeVans: 4,
    coldChainCompliant: 100,
    aiLatencyMs: 78,
    co2SavedKg: 36500,
  });

  // Modals & Toasts
  const [isDemoModalOpen, setIsDemoModalOpen] = useState(false);
  const [demoInitialVolume, setDemoInitialVolume] = useState(50000);
  const [isSurplusModalOpen, setIsSurplusModalOpen] = useState(false);
  const [toasts, setToasts] = useState([
    {
      id: 'toast-init',
      type: 'info',
      title: 'Punjab Cold-Chain Grid Active',
      message: 'Ludhiana Central Hub connected with Verka cooperatives, Mandi terminals & Langar kitchens.'
    }
  ]);

  const addToast = (toast) => {
    const id = 'toast-' + Date.now();
    setToasts((prev) => [...prev, { ...toast, id }]);
    setTimeout(() => {
      dismissToast(id);
    }, 5000);
  };

  const dismissToast = (id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  // Scenario Simulations (Punjab Environmental Shifts)
  const handleSelectScenario = (scenario) => {
    setActiveScenario(scenario);

    if (scenario === 'heatwave') {
      setWeather({
        ...weather,
        tempF: 111,
        tempC: 43.8,
        humidity: 84,
        condition: 'Severe Punjab Loo & Heatwave Alert (Decay x1.85)',
        perishabilityMultiplier: 1.85,
        heatwaveActive: true
      });

      setCategories((prev) =>
        prev.map((cat) => ({
          ...cat,
          currentEstimatedHoursRemaining: Math.max(3, Math.round(cat.currentEstimatedHoursRemaining * 0.6)),
          riskRating: cat.category.includes('Milk') || cat.category.includes('Langar') ? 'CRITICAL HAZARD - 44°C Loo' : cat.riskRating
        }))
      );

      addToast({
        type: 'warning',
        title: '☀️ Severe Punjab Loo Heatwave (44°C)',
        message: 'Decay multiplier spiked to x1.85. Tata Ace EV & Ashok Leyland Reefer units locked to 2°C target.'
      });
    } else if (scenario === 'flash_surplus') {
      const newSurplusLbs = 2400;
      const newMatch = {
        id: 'match-' + Date.now(),
        matchScore: 99.6,
        urgencyLevel: 'critical',
        donorId: 'donor-01',
        donorName: 'Verka Dairy Cooperative Complex (Ludhiana)',
        recipientId: 'recip-01',
        recipientName: 'Sri Guru Ram Dass Ji Langar (Amritsar)',
        itemCategory: 'Chilled Verka Milk & Fresh Curd',
        itemName: '2,400 lbs Verka Pasteurized Milk & Dahi Pouches',
        batchWeightLbs: 2400,
        mealsEquivalent: 2000,
        spoilageWindowHours: 12,
        estimatedTransitMins: 22,
        assignedVehicleId: 'van-02',
        assignedVehicleName: 'Ashok Leyland Cold Carrier',
        co2SavedKg: 6000,
        matchFactors: {
          proximityScore: '96% (NH44 Express Route)',
          perishabilityUrgency: 'Critical (12h cold window under heat)',
          recipientNeedScore: '99% (Langar meal prep restock)',
          dietaryCompatibility: '100% (Strict Lacto-Vegetarian)',
          coldChainCompliance: 'Assigned Ashok Leyland Reefer @ 2.5°C',
        },
        status: 'Pending Dispatch',
        aiRationale: 'Flash Verka dairy surplus drop matched to Golden Temple Langar with 99.6% Pareto multi-objective score.'
      };

      setMatches((prev) => [newMatch, ...prev]);
      setStats((prev) => ({
        ...prev,
        rescuedLbs: prev.rescuedLbs + newSurplusLbs,
        co2SavedKg: prev.co2SavedKg + 6000
      }));

      addToast({
        type: 'success',
        title: '⚡ Verka Dairy Surplus Ingested (+2,400 lbs)',
        message: 'AI allocated 2,400 lbs fresh dairy to Golden Temple Langar with 99.6% compatibility score.'
      });
    } else if (scenario === 'shelter_surge') {
      setRecipients((prev) =>
        prev.map((r) =>
          r.id === 'recip-01'
            ? { ...r, urgencyScore: 99, currentStockHours: 2.0, dailyDemandMeals: 55000 }
            : r
        )
      );

      addToast({
        type: 'warning',
        title: '👥 Langar Pilgrim Surge in Amritsar',
        message: 'Demand spiked to 55,000 meals. AI matching algorithm elevated GT Highway supply priority.'
      });
    } else if (scenario === 'traffic_reroute') {
      setFleet((prev) =>
        prev.map((v) =>
          v.id === 'van-02'
            ? { ...v, assignedRoute: 'Jalandhar -> Amritsar (Via Phagwara NH44 Bypass)', etaMinutes: 19, tempStatus: 'Optimal (2.8°C)' }
            : v
        )
      );

      addToast({
        type: 'info',
        title: '🛑 GT Road Traffic Bypass Computed',
        message: 'Ashok Leyland Cold Carrier auto-rerouted around Phagwara congestion. Cold-chain integrity preserved.'
      });
    }
  };

  const handleResetBaseline = () => {
    setActiveScenario('baseline');
    setWeather(INITIAL_WEATHER);
    setCategories(PERISHABILITY_CATEGORIES);
    setRecipients(RECIPIENTS);
    setFleet(INITIAL_FLEET);
    setMatches(INITIAL_MATCH_RECOMMENDATIONS);
    setDistricts(DISTRICT_DEMAND_FORECAST);
    addToast({
      type: 'info',
      title: 'Punjab Operational Baseline Restored',
      message: 'System reset to default telemetry and active GT road dispatches.'
    });
  };

  // Dispatch Action
  const handleDispatchMatch = (matchId) => {
    setMatches((prev) =>
      prev.map((m) =>
        m.id === matchId ? { ...m, status: 'Dispatched' } : m
      )
    );

    const match = matches.find((m) => m.id === matchId);
    if (match) {
      addToast({
        type: 'success',
        title: `🚚 Dispatched: ${match.assignedVehicleName}`,
        message: `Routed from ${match.donorName} to ${match.recipientName}. (${match.batchWeightLbs} lbs / ~${match.mealsEquivalent} meals)`
      });
    }
  };

  // Add Surplus Submission
  const handleAddSurplus = (newBatch) => {
    const newMatch = {
      id: 'match-' + Date.now(),
      matchScore: 98.1,
      urgencyLevel: newBatch.urgencyLevel,
      donorId: 'donor-custom',
      donorName: newBatch.donorName,
      recipientId: 'recip-01',
      recipientName: 'Sri Guru Ram Dass Ji Langar (Amritsar)',
      itemCategory: newBatch.category,
      itemName: `${newBatch.weightLbs} lbs ${newBatch.itemName}`,
      batchWeightLbs: newBatch.weightLbs,
      mealsEquivalent: Math.round(newBatch.weightLbs * 0.83),
      spoilageWindowHours: newBatch.shelfLifeHours,
      estimatedTransitMins: 18,
      assignedVehicleId: 'van-01',
      assignedVehicleName: 'Tata Ace EV Reefer',
      co2SavedKg: Math.round(newBatch.weightLbs * 2.5),
      matchFactors: {
        proximityScore: '96%',
        perishabilityUrgency: `${newBatch.shelfLifeHours}h safe shelf window`,
        recipientNeedScore: '95% Langar need match',
        dietaryCompatibility: '100% Pure Lacto-Veg',
        coldChainCompliance: newBatch.tempReq,
      },
      status: 'Pending Dispatch',
      aiRationale: `Newly logged surplus from ${newBatch.donorName} automatically queued for optimal redistribution in Punjab grid.`
    };

    setMatches((prev) => [newMatch, ...prev]);
    setStats((prev) => ({
      ...prev,
      rescuedLbs: prev.rescuedLbs + newBatch.weightLbs,
      co2SavedKg: prev.co2SavedKg + Math.round(newBatch.weightLbs * 2.5)
    }));

    addToast({
      type: 'success',
      title: '✅ Surplus Ingested into Punjab Grid',
      message: `${newBatch.weightLbs} lbs of ${newBatch.itemName} queued for dispatch.`
    });
  };

  const handleOpenDemoWithVolume = (vol) => {
    setDemoInitialVolume(vol);
    setIsDemoModalOpen(true);
  };

  return (
    <div>
      {/* ── ROUTE 1: STANDALONE OPERATIONS CONSOLE PAGE (PUNJAB STATE GRID) ── */}
      {currentRoute === 'console' ? (
        <OperationsApp 
          weather={weather}
          donors={donors}
          hubs={hubs}
          recipients={recipients}
          fleet={fleet}
          matches={matches}
          categories={categories}
          districts={districts}
          endpoints={AI_INTEGRATION_ENDPOINTS}
          stats={stats}
          activeScenario={activeScenario}
          onSelectScenario={handleSelectScenario}
          onResetScenario={handleResetBaseline}
          onDispatchMatch={handleDispatchMatch}
          onLogSurplus={() => setIsSurplusModalOpen(true)}
          onNavigateHome={navigateToLanding}
        />
      ) : (
        /* ── ROUTE 2: PUBLIC LANDING PAGE ── */
        <div className="landing-page-wrap">
          <Navbar 
            onRequestDemo={() => setIsDemoModalOpen(true)}
            onScrollToConsole={navigateToConsole}
          />

          <Hero 
            onRequestDemo={() => setIsDemoModalOpen(true)}
            onExploreConsole={navigateToConsole}
          />

          {/* Clean Dashboard Showcase Teaser with Launch Action */}
          <DashboardTeaser 
            stats={stats}
            weather={weather}
            onLaunchConsole={navigateToConsole}
            onRequestDemo={() => setIsDemoModalOpen(true)}
          />

          <HowItWorks />

          <ImpactCalculatorSection 
            onRequestDemoWithVolume={handleOpenDemoWithVolume}
          />

          <ComparisonSection />

          <Footer 
            onRequestDemo={() => setIsDemoModalOpen(true)}
          />
        </div>
      )}

      {/* Interactive Modals */}
      <RequestDemoModal 
        isOpen={isDemoModalOpen}
        onClose={() => setIsDemoModalOpen(false)}
        initialWeeklyVolume={demoInitialVolume}
        onScheduleSuccess={(details) => {
          addToast({
            type: 'success',
            title: '🎉 Showcase Demo Booked',
            message: `Confirmed for ${details.name} (${details.organization}). Impact projection: ~${(details.annualMeals / 1000).toFixed(0)}k meals/yr.`
          });
        }}
      />

      <LogSurplusModal 
        isOpen={isSurplusModalOpen}
        onClose={() => setIsSurplusModalOpen(false)}
        onAddSurplus={handleAddSurplus}
        donors={donors}
      />

      {/* Global Notification Toasts */}
      <ToastContainer 
        toasts={toasts}
        onDismiss={dismissToast}
      />
    </div>
  );
}
