# K14 reading brief

**Event line:** July 31, 2025: an underground tunnel collapsed at Codelco's El Teniente copper mine in Chile.

**Node (use this id verbatim as the `from` of your first hop):** `el_teniente_copper_supply`

## What you are asked

Read the documents in `docs/` (nothing else: no web, no memory of later events, no other files). Find entities that are **within reach** of the node and either **fill a role in a forced or switch derivation**, or are **expressible**, or are **one documented relation from an entity that is expressible**.

- *Within reach:* a chain of documented relations from the node to the entity. Every hop names a relation type from the registry below, an effect kind pair (from-effect > to-effect) that the registry lists for that relation, a document id, and an **exact quoted span** from that document. A script (not you) multiplies transform value x discount along the chain and requires the product to stay at or above **0.3**; do not compute it. A hop with no quotable support in the documents is not a hop.
- *Fills a role in a forced or switch derivation:* the entity has the capability a template role requires (templates below), so it would be the obligor, the governing document or a carrier of an obligation that a documented fact forces or could switch.
- *Expressible:* a listed instrument (a share, bond, option, future, ETF, event contract) references the entity directly, and a document says so.
- *One documented relation from an entity that is expressible:* a relation from the entity to another entity that is expressible, documented with a quote. This is how a person (by office) or a document counts.
- Persons: name the **office and organisation only** ("the chief financial officer of X"), never a personal name.
- If you are unsure a hop is documented, leave the find out. A short list of well-supported finds is worth more than a long one. At most 8 finds per reading.

## The two readings

**Open reading:** any kind in the registry that is *not* marked v16-holdable, using any relation type. Kinds marked *unreviewed* propose only and cannot support: do not use them as finds.
**Closed reading:** the same documents, but only kinds marked v16-holdable and only the sixteen v16 relation types (offtake, input_supply, input_cost, ownership, shared_facility, shared_infrastructure, logistics, regulatory_scope, customer, competitor, substitute, grid_neighbour, lender, insurer, regulator, counterparty).
Do both in one session, in the order given in your instructions. The order alternates by round so that the second reading does not always benefit from the first.

## Output

Write `finds_open.json` and `finds_closed.json` next to `package.json`, each `{"finds": [...]}` with, per find:

```json
{"find_id": "O1", "entity": {"name": "...", "kind": "<registry kind>", "evidence": {"doc": "D1", "quote": "exact span"}},
 "chain": [{"from": "<node id or previous to>", "relation": "<registry relation>", "to": "...", "from_effect": "state", "to_effect": "availability", "doc": "D1", "quote": "exact span"}],
 "expression": {"claim": "role|expressible|one_hop_from_expressible", "detail": "one or two sentences", "entity": "the expressible entity (if one_hop)", "relation": "registry relation (if one_hop)", "doc": "D?", "quote": "exact span (if one_hop)"}}
```

The chain's last `to` must equal the entity's `name`. Also write `reading_notes.md`: two or three lines on what you found hard.

## Registry: entity kinds

| kind | parent | review | v16 could hold | capabilities |
|---|---|---|---|---|
| organisation |  | reviewed | no | party_to_contract |
| company | organisation | reviewed | yes | operates_assets, issues_debt, has_operating_scale |
| agency | organisation | reviewed | yes |  |
| central_bank | organisation | reviewed | yes |  |
| court | organisation | reviewed | no |  |
| exchange | organisation | reviewed | no |  |
| cooperative | organisation | reviewed | no |  |
| fund | organisation | reviewed | yes |  |
| sovereign | organisation | reviewed | yes | issues_debt, controls |
| facility |  | reviewed | yes | has_operating_scale |
| plant | facility | reviewed | yes |  |
| reactor_unit | facility | reviewed | yes |  |
| mine | facility | reviewed | yes |  |
| field | facility | reviewed | yes |  |
| vessel | facility | reviewed | yes |  |
| pipeline | facility | reviewed | yes |  |
| port | facility | reviewed | yes |  |
| data_centre | facility | reviewed | yes |  |
| warehouse | facility | reviewed | yes |  |
| person |  | reviewed | no | holds_office, controls |
| instrument |  | unreviewed | no |  |
| share | instrument | unreviewed | no |  |
| bond | instrument | unreviewed | no |  |
| option | instrument | unreviewed | no |  |
| future | instrument | unreviewed | no |  |
| etf | instrument | unreviewed | no |  |
| event_contract | instrument | unreviewed | no |  |
| cds | instrument | unreviewed | no |  |
| commodity_grade |  | unreviewed | yes |  |
| currency |  | unreviewed | yes |  |
| index |  | unreviewed | yes |  |
| place |  | unreviewed | no |  |
| region | place | unreviewed | no |  |
| zone | place | unreviewed | no |  |
| strait | place | unreviewed | no |  |
| port_area | place | unreviewed | no |  |
| hazard_area | place | unreviewed | no |  |
| document |  | reviewed | no | party_to_contract |
| filing | document | reviewed | no |  |
| contract | document | reviewed | yes |  |
| statute | document | reviewed | no |  |
| regulation | document | reviewed | no |  |
| licence | document | reviewed | no |  |
| tariff | document | reviewed | no |  |
| notice | document | reviewed | no |  |
| ruling | document | reviewed | no |  |
| report | document | reviewed | no |  |
| release | document | reviewed | no |  |
| dataset | document | reviewed | no |  |
| document_series |  | unreviewed | no |  |
| composite |  | unreviewed | yes |  |
| supply_chain | composite | unreviewed | yes |  |
| corridor | composite | unreviewed | yes |  |
| market | composite | unreviewed | yes |  |
| ownership_group | composite | unreviewed | yes |  |
| cluster | composite | unreviewed | yes |  |
| regime | composite | unreviewed | yes |  |
| class | composite | unreviewed | yes |  |
| story |  | unreviewed | no |  |
| factor |  | unreviewed | no |  |

## Registry: capabilities

- `party_to_contract`: Can be bound by a document
- `files_reports`: Files periodic or event reports with a regulator or exchange
- `issues_debt`: Has or can have coupons and maturities
- `operates_assets`: Operates facilities
- `holds_office`: Can hold an office
- `controls`: Can be the controlling party in a control relation
- `has_operating_scale`: Has a scale attribute
- `expressible`: At least one instrument references it directly
- `expressible_by_proxy`: An instrument references an entity it is documented to be exposed to
- `observable_by`: A reports_on edge from a series of that carrier kind exists

## Registry: relation types (discount; effect pairs with transform value)

| relation | discount | pairs |
|---|---|---|
| adjacent_to | 0.0 | does not transmit: classificatory; scope only |
| amends | 0.9 | state>state 0.9 |
| analogy | 0.0 | does not transmit: analogical |
| binds | 0.8 | state>obligation 0.9; state>availability 0.6; state>cost 0.5; state>revenue 0.5 |
| classified_as | 0.0 | does not transmit: classificatory; proposes only |
| competitor | 0.4 | volume>price 0.4; volume>volume 0.3; availability>price 0.4; availability>revenue 0.4 |
| controls | 0.75 | control>direction 0.6; control>obligation 0.5; state>control 0.7 |
| counterparty | 0.6 | obligation>revenue 0.5; obligation>cost 0.5; cost>obligation 0.0 |
| coverage | 0.0 | does not transmit: attentional |
| customer | 0.5 | volume>revenue 0.7; availability>revenue 0.5 |
| evidences | 0.0 | does not transmit: provenance |
| governs | 0.6 | state>availability 0.8; state>obligation 0.7; state>cost 0.5; state>timing 0.5 |
| grid_neighbour | 0.5 | availability>price 0.5; volume>price 0.5; price>revenue 0.6; price>cost 0.6 |
| holds_office_at | 0.6 | state>control 0.7 |
| index_membership | 0.0 | does not transmit: analogical |
| input_cost | 0.65 | cost>cost 0.85; cost>direction 0.5; cost>obligation 0.0 |
| input_supply | 0.7 | volume>volume 0.9; volume>cost 0.85; volume>obligation 0.6; cost>cost 0.8; price>cost 0.8; availability>volume 0.6; availability>obligation 0.5 |
| insurer | 0.4 | availability>cost 0.4 |
| issued_by | 0.0 | does not transmit: provenance |
| lender | 0.5 | credit>credit 0.5; revenue>credit 0.3 |
| listing_venue | 0.0 | does not transmit: analogical |
| located_at | 0.6 | availability>availability 0.6; timing>timing 0.4 |
| logistics | 0.65 | timing>timing 0.8; volume>timing 0.7; volume>volume 0.6 |
| member_of | 0.0 | does not transmit: computed by recomputation (§4.3); no table entry |
| offtake | 0.7 | volume>volume 0.9; volume>cost 0.8; volume>obligation 0.0; volume>timing 0.5; cost>cost 0.8; direction>direction 0.5; price>cost 0.8; availability>volume 0.5 |
| ownership | 0.85 | direction>direction 0.9; volume>direction 0.7; cost>direction 0.7; obligation>obligation 0.5; volume>volume 1.0; volume>revenue 1.0; revenue>revenue 1.0; cost>cost 1.0; availability>availability 1.0; availability>revenue 0.9; margin>margin 1.0; credit>credit 0.8 |
| references | 0.0 | does not transmit: expression edge |
| regulator | 0.7 | availability>obligation 0.8; obligation>obligation 0.7 |
| regulatory_scope | 0.6 | obligation>obligation 0.8; timing>timing 0.6; obligation>cost 0.5 |
| reporting_currency | 0.0 | does not transmit: analogical |
| reports_on | 0.0 | does not transmit: provenance |
| sector | 0.0 | does not transmit: analogical |
| shared_facility | 0.75 | volume>volume 0.8; timing>timing 0.7; volume>obligation 0.0 |
| shared_infrastructure | 0.7 | volume>volume 0.75; timing>timing 0.7 |
| size_bucket | 0.0 | does not transmit: analogical |
| substitute | 0.5 | availability>demand 0.5; price>demand 0.5 |
| supersedes | 0.9 | state>state 0.9 |

## Effect kinds

volume, cost, price, revenue, obligation, availability, credit, margin, demand, timing, direction, state, control

## Obligation templates (what forces an ACK)

- `obl.written_event_report` (power_reactor): A licensee that made an immediate notification of a reportable event, under a regime requiring a written follow-up, must file the written report within the statutory window. Roles: licensee (needs `licensed_facility`)
- `obl.unit_status_publication` (power_reactor, power_plant): A unit taken offline, under a regulator that publishes every unit's status daily, must appear either restarted or still down in each daily report; its return to service is published. Roles: operator (needs `unit_status`)
- `obl.material_event_current_report` (power_reactor, power_plant, refinery, smelter, port, pipeline, lng_terminal, chemical_plant, mine, strait, data_centre, cloud_region): A listed issuer for which an event is material must file a current report within the statutory window. Roles: issuer (needs `listed_domestic_filer`)
- `obl.force_majeure_notice` (smelter, refinery, mine, lng_terminal, chemical_plant, power_plant, pipeline, port): A supplier that can't deliver contracted offtake, with no substitute inside the window and buyers' inventory below the window, must notify its counterparties. Roles: supplier (needs `capacity_lost_share`), buyer (needs `contract_type`)
- `obl.allocation_notice` (smelter, refinery, mine, lng_terminal, chemical_plant, pipeline): A supplier short of contracted volume with several contracted buyers must allocate and notify the allocation. Roles: supplier (needs `capacity_lost_share`)
- `obl.regulator_decision` (power_reactor, power_plant, pipeline, port, lng_terminal, strait, sovereign_debt, central_bank_facility): A regulator with a pending application under a statutory decision window must answer inside it. Roles: applicant (needs `pending_application`)
- `obl.war_risk_notice` (strait, port, shipping_lane): An insurer covering transits of a node that becomes a declared risk area must give notice of cancellation or re-rating within its policy notice period. Roles: insurer (needs `covers_node_transit`)
- `obl.sovereign_payment` (sovereign_debt): A sovereign with a coupon due inside the window must pay, pay in grace, or miss; the payment status is published. Roles: issuer (needs `coupon_due_days`)
- `obl.replacement_procurement` (power_reactor, power_plant): An owner with an obligation to serve load, whose owned share of an offline unit exceeds its uncommitted capacity, must buy replacement energy or capacity for the outage. Roles: owner (needs `owns_unit`)
