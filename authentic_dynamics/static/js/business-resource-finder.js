'use strict';

const finder = document.querySelector('[data-resource-finder]');

if (finder) {
  const countySelect = finder.querySelector('#resource-county');
  const needSelect = finder.querySelector('#resource-need');
  const emptyState = finder.querySelector('[data-resource-empty]');
  const resultsHead = finder.querySelector('[data-results-head]');
  const resultCount = finder.querySelector('[data-result-count]');
  const results = finder.querySelector('[data-resource-results]');
  const resetButton = finder.querySelector('[data-resource-reset]');
  const resourceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  let resultTransition;
  resourceMotion.addEventListener('change', () => resultTransition?.cancel());

  const counties = {
    cumberland: { name: 'Cumberland County', sbdc: 'Shippensburg University SBDC' },
    dauphin: { name: 'Dauphin County', sbdc: 'Kutztown University SBDC' },
    lancaster: { name: 'Lancaster County', sbdc: 'Kutztown University SBDC' },
    lebanon: { name: 'Lebanon County', sbdc: 'Kutztown University SBDC' },
    perry: { name: 'Perry County', sbdc: 'Bucknell University SBDC' },
    york: { name: 'York County', sbdc: 'Shippensburg University SBDC' }
  };

  const localResources = {
    cumberland: {
      title: 'Cumberland Area Economic Development Corporation',
      description: 'Local help for starting, financing, locating, redeveloping or expanding a business in Cumberland County.',
      url: 'https://cumberlandbusiness.com/our-services/overview/',
      needs: ['start', 'advice', 'funding', 'location']
    },
    dauphin: {
      title: 'Dauphin County Community & Economic Development',
      description: 'County programs and staff supporting business development, local financing and community investment.',
      url: 'https://www.dauphincounty.gov/government/support-services/community-and-economic-development',
      needs: ['advice', 'funding', 'location']
    },
    lancaster: {
      title: 'EDC Lancaster County',
      description: 'Business-growth guidance, economic data and financing connections for Lancaster County companies.',
      url: 'https://www.edclancaster.com/',
      needs: ['advice', 'funding', 'location']
    },
    lebanon: {
      title: 'Lebanon Valley Economic Development Corporation',
      description: 'Lebanon County’s economic-development resource for business investment, expansion and site needs.',
      url: 'https://www.lvedc.org/',
      needs: ['advice', 'funding', 'location']
    },
    perry: {
      title: 'Perry County Economic Development Authority',
      description: 'Local mentoring, organizational support, learning opportunities and funding connections for Perry County businesses.',
      url: 'https://perrycountyeda.com/economic-development',
      needs: ['start', 'advice', 'funding', 'location', 'training']
    },
    york: {
      title: 'York County Economic Alliance',
      description: 'York County support for business growth, financing, redevelopment, connections and workforce needs.',
      url: 'https://www.yceapa.org/resources/partner-resources/',
      needs: ['advice', 'funding', 'location', 'training']
    }
  };

  const statewideResources = [
    {
      title: 'Pennsylvania Business One-Stop Shop',
      scope: 'Commonwealth of Pennsylvania',
      description: 'Official guidance for planning, registering, operating and growing a business in Pennsylvania.',
      url: 'https://business.pa.gov/',
      needs: ['start', 'advice', 'funding', 'location', 'permits']
    },
    {
      title: 'Pennsylvania SBDC',
      scope: 'Local center',
      description: 'No-cost, confidential consulting plus training and business resources through your county’s assigned center.',
      url: 'https://www.pasbdc.org/',
      needs: ['start', 'advice', 'funding', 'location', 'permits', 'training']
    },
    {
      title: 'Pennsylvania Department of State — Business',
      scope: 'Commonwealth of Pennsylvania',
      description: 'Official business filing, registration and record information from Pennsylvania’s state record keeper.',
      url: 'https://www.pa.gov/agencies/dos/programs/business',
      needs: ['start', 'permits']
    }
  ];

  const createCard = resource => {
    const article = document.createElement('article');
    article.className = 'resource-card';

    const meta = document.createElement('div');
    meta.className = 'resource-card-scope';
    const scope = document.createElement('span');
    scope.textContent = resource.scope;
    const verified = document.createElement('span');
    verified.textContent = 'Verified source';
    meta.append(scope, verified);

    const heading = document.createElement('h3');
    heading.textContent = resource.title;
    const description = document.createElement('p');
    description.textContent = resource.description;
    const link = document.createElement('a');
    link.href = resource.url;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.textContent = 'Visit official resource';
    const arrow = document.createElement('span');
    arrow.setAttribute('aria-hidden', 'true');
    arrow.textContent = '↗';
    link.append(arrow);

    article.append(meta, heading, description, link);
    return article;
  };

  const render = () => {
    const countyKey = countySelect.value;
    const need = needSelect.value;
    resultTransition?.cancel();
    results.replaceChildren();

    if (!countyKey || !counties[countyKey]) {
      emptyState.hidden = false;
      resultsHead.hidden = true;
      return;
    }

    const county = counties[countyKey];
    const local = localResources[countyKey];
    const resources = [
      { ...local, scope: county.name },
      ...statewideResources.map(resource => resource.title === 'Pennsylvania SBDC'
        ? { ...resource, title: county.sbdc, scope: 'Pennsylvania SBDC network' }
        : resource)
    ].filter(resource => need === 'all' || resource.needs.includes(need));

    emptyState.hidden = true;
    resultsHead.hidden = false;
    const needName = needSelect.options[needSelect.selectedIndex].text.toLowerCase();
    const resultLabel = `${resources.length} trusted starting point${resources.length === 1 ? '' : 's'}`;
    resultCount.textContent = need === 'all'
      ? `${resultLabel} for ${county.name}`
      : `${resultLabel} for ${needName} in ${county.name}`;

    if (!resources.length) {
      const noMatch = document.createElement('div');
      noMatch.className = 'resource-no-match';
      noMatch.innerHTML = '<h3>No exact match yet.</h3><p>Try “Any current need,” or contact the county resource for a referral.</p>';
      results.append(noMatch);
      return;
    }
    resources.forEach(resource => results.append(createCard(resource)));
    if (!resourceMotion.matches && results.animate) {
      resultTransition = results.animate([{ opacity: .65 }, { opacity: 1 }], {
        duration: 160, easing: 'ease-out'
      });
    }
  };

  countySelect.addEventListener('change', render);
  needSelect.addEventListener('change', render);
  resetButton.addEventListener('click', () => {
    countySelect.value = '';
    needSelect.value = 'all';
    render();
    countySelect.focus();
  });
}
