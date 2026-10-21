/* Local, fictional service demonstrations. No storage, uploads or integrations. */
'use strict';
(() => {
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const animations = new Set();
  const emphasize = panel => {
    if (reducedMotion.matches || typeof panel.animate !== 'function') return;
    const animation = panel.animate(
      [{opacity: 0.65, transform: 'translateY(3px)'}, {opacity: 1, transform: 'translateY(0)'}],
      {duration: 180, easing: 'ease-out'},
    );
    animations.add(animation);
    animation.onfinish = () => animations.delete(animation);
  };
  reducedMotion.addEventListener('change', () => {
    if (reducedMotion.matches) {
      animations.forEach(animation => animation.cancel());
      animations.clear();
    }
  });
  const setText = (id, text) => { document.getElementById(id).textContent = text; };
  const website = document.getElementById('website-experience');
  if (website) {
    const goals = {
      inquiries: {
        title: 'A little help for your outdoor space.',
        copy: 'Understand the service, check the fit, then start a conversation.',
        kicker: 'LOCAL SERVICE / CLEAR NEXT STEP',
        detail: 'Garden care · Seasonal cleanup · Small outdoor projects',
        action: 'Try an inquiry',
        preview: 'Example request: Sam in Camp Hill would like help with a seasonal garden cleanup.',
        next: 'Preview the next step',
        completed: 'Sam sees what happens next: the business reviews the request and replies to discuss scope. Nothing was sent.',
        scope: 'Clear services, real coverage and a simple inquiry path. A focused site can start at $500; exact scope is agreed first.',
        interest: 'website',
      },
      booking: {
        title: 'Make room for a garden conversation.',
        copy: 'Explain the visit, offer a clear choice and confirm what happens next.',
        kicker: 'APPOINTMENTS / EXPECTATIONS FIRST',
        detail: 'Example: a 20-minute garden planning conversation. Times here are fictional.',
        action: 'Choose a sample time',
        preview: 'Sample choice: Tuesday at 10:00 a.m. This is an example request, not live availability.',
        next: 'Preview a visit request',
        completed: 'The example asks the business to confirm the time before a visit is booked. No appointment was created.',
        scope: 'A simple booking inquiry can be part of a focused site. Live availability, reminders and scheduling-provider fees need a separate scope.',
        interest: 'custom',
      },
      catalog: {
        title: 'Help people find the right fit.',
        copy: 'Show a clear product choice and an easy way to ask about it.',
        kicker: 'PRODUCTS / USEFUL DETAILS',
        detail: 'Example collection: pollinator plants, kitchen herbs and seasonal planters.',
        action: 'Explore a sample product',
        preview: 'Sample product: a kitchen herb planter for a sunny outdoor spot. Ask the business about options and availability.',
        next: 'Preview a product inquiry',
        completed: 'The example inquiry identifies the herb planter so the business can answer the right question. No order or message was sent.',
        scope: 'A product showcase helps people explore before asking. Checkout, inventory and payment integrations are quoted separately.',
        interest: 'custom',
      },
    };
    let current = 'inquiries';
    let stage = 0;
    const buttons = [...website.querySelectorAll('[data-website-goal]')];
    const action = document.getElementById('website-demo-action');
    const render = (announce = true) => {
      const goal = goals[current];
      buttons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.websiteGoal === current)));
      setText('website-demo-title', goal.title);
      setText('website-demo-copy', goal.copy);
      setText('website-demo-kicker', goal.kicker);
      setText('website-demo-detail', stage === 0 ? goal.detail : stage === 1 ? goal.preview : goal.completed);
      action.textContent = stage === 0 ? goal.action : stage === 1 ? goal.next : 'Start this example again';
      setText('website-demo-scope', goal.scope);
      const contact = document.getElementById('website-demo-contact');
      const url = new URL(contact.href, window.location.href);
      url.searchParams.set('interest', goal.interest);
      contact.href = `${url.pathname}${url.search}#contact`;
      if (announce) setText('website-demo-status', stage === 2 ? 'Example complete. Nothing was sent or saved.' : `${stage === 0 ? 'Example ready.' : 'Sample selected.'} Preview only; no information is collected or sent.`);
      emphasize(document.getElementById('website-demo-panel'));
    };
    buttons.forEach(button => button.addEventListener('click', () => {
      current = button.dataset.websiteGoal;
      stage = 0;
      render();
    }));
    action.addEventListener('click', () => { stage = (stage + 1) % 3; render(); });
    website.querySelectorAll('[data-service-controls]').forEach(control => { control.hidden = false; });
  }

  const growth = document.getElementById('growth-experience');
  if (growth) {
    const workflows = {
      followup: {
        recommendation: 'Connect the inquiry to an owner, a clear response and a trackable next step.',
        interest: 'automation', cta: 'Talk about follow-up', labels: ['Inquiry', 'Review', 'Follow-up'],
        steps: [
          ['A clear request', 'Sam asks a fictional garden business about seasonal cleanup in Camp Hill.', 'One place to start', 'The example inquiry is collected in a single record. No message has been sent.'],
          ['Useful expectations', 'Sam can see that the business will review the request before promising a time or price.', 'A person checks the fit', 'The owner checks coverage and capacity. An uncertain or unusual request stays with a person.'],
          ['An agreed next step', 'The example reply asks Sam to choose a time for a conversation, not an automatically confirmed job.', 'Visible follow-through', 'The owner records the next action. A failed connection would need an alert and a manual fallback.'],
        ],
      },
      visibility: {
        recommendation: 'Start with accurate business details and a useful page for the service customers need.',
        interest: 'growth', cta: 'Talk about local visibility', labels: ['Details', 'Service', 'Next step'],
        steps: [
          ['Find the right details', 'Sam wants to know whether a garden business serves Camp Hill.', 'Keep the basics accurate', 'The owner maintains actual services, hours and coverage. This example does not check or change a business listing.'],
          ['Understand the service', 'Sam reads what a seasonal cleanup includes before deciding to ask.', 'Answer real questions', 'The service page explains the work and its limits. No search position or traffic result is promised.'],
          ['Reach a real person', 'Sam follows the inquiry path with the service already in mind.', 'Review what happened', 'A real implementation can measure useful actions with an agreed analytics setup. No tracking is running in this example.'],
        ],
      },
      inquiries: {
        recommendation: 'Make the offer, fit and next action clear before asking customers to fill anything out.',
        interest: 'website', cta: 'Talk about the inquiry path', labels: ['Question', 'Decision', 'Inquiry'],
        steps: [
          ['A specific question', 'Sam wants help with an outdoor space and needs to know what the business offers.', 'A focused page', 'The example leads with the relevant service instead of a long list of unrelated options.'],
          ['Enough to decide', 'Sam checks coverage, the process and what information would help the business respond.', 'Clear boundaries', 'The business explains what happens after an inquiry without promising availability or price it cannot confirm.'],
          ['A manageable request', 'Sam reaches a short form that keeps the chosen service editable.', 'Useful context', 'A real inquiry can carry that service choice to the owner. This simulation has no form submission or external connection.'],
        ],
      },
    };
    let current = 'followup';
    let step = 0;
    const choices = [...growth.querySelectorAll('[data-growth-goal]')];
    const steps = [...growth.querySelectorAll('[data-workflow-step]')];
    const render = () => {
      const flow = workflows[current];
      choices.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.growthGoal === current)));
      steps.forEach((button, index) => {
        button.textContent = `${index + 1} · ${flow.labels[index]}`;
        if (index === step) button.setAttribute('aria-current', 'step');
        else button.removeAttribute('aria-current');
      });
      setText('growth-recommendation', flow.recommendation);
      ['growth-customer-title', 'growth-customer-copy', 'growth-owner-title', 'growth-owner-copy'].forEach((id, index) => setText(id, flow.steps[step][index]));
      setText('growth-demo-status', `Example step ${step + 1} of 3: ${flow.labels[step]}. Nothing is connected or sent.`);
      const contact = document.getElementById('growth-demo-contact');
      const url = new URL(contact.href, window.location.href);
      url.searchParams.set('interest', flow.interest);
      contact.href = `${url.pathname}${url.search}#contact`;
      contact.textContent = `${flow.cta} ↗`;
      emphasize(document.getElementById('growth-demo-panel'));
    };
    choices.forEach(button => button.addEventListener('click', () => { current = button.dataset.growthGoal; step = 0; render(); }));
    steps.forEach(button => button.addEventListener('click', () => { step = Number(button.dataset.workflowStep); render(); }));
    growth.querySelectorAll('[data-service-controls]').forEach(control => { control.hidden = false; });
  }
})();
