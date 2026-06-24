> **Already done? Start later in the course instead:**
> ```bash
> python setup/catchup.py --student student.json --checkpoint 1
> ```
> This verifies (or creates) the golden Contact record and seeds Data Cloud DMO records.
> Then continue at [Part A](#part-a-org-provisioning-and-core-setup-10-min) below.

## Exercise 1: Provision and Configure the Shared Data Cloud Environment

**Timing**: ~90 minutes  
**Purpose**: Establish the Salesforce org that provides customer context (Data Cloud) and action execution (Service Cloud) for the agentic network.

> **Important**: Standard Salesforce Developer Edition orgs do not include Data Cloud. The only reliable way to get a Developer Edition with Data Cloud enabled is through the Salesforce Developer Trial at https://www.salesforce.com/products/free-trial/developer/ — select the option that includes Data Cloud. Internal partner/training orgs often lack the correct permissions. This specific trial link is the proven path.

---

### Prerequisites

| Item | Value |
|------|-------|
| Salesforce Org | Developer Edition **with Data Cloud** — provisioned from https://www.salesforce.com/products/free-trial/developer/ (this is the only reliable source) |
| Org Username | _(your org's admin username)_ |
| Connected App Name | `Data Cloud External` (created in Part G of this exercise) |
| Consumer Key | _(obtained when creating the Connected App — Part G, Step 15)_ |
| Consumer Secret | _(stored securely — never commit to source control)_ |
| OAuth Grant Type | `client_credentials` |
| Token Endpoint | `https://<your-my-domain>.my.salesforce.com/services/oauth2/token` |

> **Note**: If you're using a pre-built training org, the instructor will provide the Consumer Key and Token Endpoint. If rebuilding from scratch, you'll create the Connected App in Part G and obtain your own credentials.

---

### Part A: Org Provisioning and Core Setup (~10 min)

#### Step 1: Verify the Org Has Data Cloud

1. Log in to the org at https://login.salesforce.com with your org admin username
2. Click the **App Launcher** (9-dot grid, top left)
3. Search for **"Data Cloud"** and click it
4. **Verify**: You should see the Data Cloud home page with tabs: Home, Data Streams, Data Model, Identity Resolutions, Segments, Calculated Insights
5. If "Data Cloud" does not appear, the org does not have the license — provision a new one from the developer trial link above

#### Step 2: Create Custom Fields on Contact

These fields will become the AI agent's grounding context (loyalty tier, churn risk).

1. Navigate to **Setup** (gear icon → Setup)
2. Click **Object Manager** (top navigation bar, next to Home)
3. In Quick Find, type **"Contact"** and click it in the object list
4. Click **Fields & Relationships** in the left sidebar
5. Click **New**

**Field 1: Loyalty Tier**

6. Select **Picklist** → click **Next**
7. Field Label: `Loyalty Tier`
8. Select **"Enter values, with each value separated by a new line"** (it defaults to "Use global picklist value set" — you must change this)
9. Enter these values (one per line):
   ```
   Platinum
   Gold
   Silver
   ```
10. Check **"Use first value as default value"** (this will default the field to `Platinum`, which is already the first value in the list)
11. Click **Next** → **Next** → **Save & New**

**Field 2: Churn Risk**

12. Select **Picklist** → click **Next**
13. Field Label: `Churn Risk`
14. Select **"Enter values, with each value separated by a new line"**
15. Enter these values (one per line — put `Low` first since that's the default we want):
    ```
    Low
    Medium
    High
    ```
16. Check **"Use first value as default value"** (this will default the field to `Low`, which is the first value in the list)
17. Click **Next** → **Next** → **Save**

#### Step 3: Create the Golden Contact Record

This is the contact the AI agent will look up. The email MUST match the Slack user email used in testing.

1. Click the **App Launcher** → search **"Contacts"** → click Contacts
2. Click **New**
3. Fill in:
   - First Name: `Sarah`
   - Last Name: `Chen`
   - Email: `student-slack-test@globaltech.com`
   - Loyalty Tier: `Platinum`
   - Churn Risk: `Low`
4. Click **Save**
5. **Record the Contact ID** from the URL (e.g., `003gL00000fwf81QAA`) — you'll need this later for verification

> **Critical**: The Email field must EXACTLY match the email of the Slack account students will test with. When the agent does an On-Behalf-Of (OBO) lookup, it queries Data Cloud by email. If there's no match, the query returns empty and the agent has no customer context.

---

### Part B: Initialize Data Cloud (~10 min)

In a fresh org, Data Cloud must be provisioned before you can access Data Streams or Data Model features.

#### Step 4: Run the Data Cloud Setup Wizard

1. Navigate to **Setup** → Quick Find → search **"Data Cloud"** → click **Data Cloud Setup Home**
2. You will see the **"Welcome to Data Cloud"** page with a "Set Up Data Cloud" section
3. Under **"Set Up Your Data Cloud Instance"**, click the **Get Started** button
4. Wait for the 4 automated steps to complete:
   - Creating your Data Cloud instance
   - Setting up your metadata
   - Initializing the Customer 360 Data Model
   - Making sure everything is ready to go
5. This process runs in the background — you can navigate away and come back. Typically takes 2-5 minutes.
6. **Verify**: Once complete, open the **App Launcher** (9-dot grid) → search **"Data Cloud"** → click it. You should now see the full Data Cloud app with tabs: Data Streams, Data Model, Identity Resolutions, etc.

> **If you skip this step**, the Data Cloud app will not show Data Streams or Data Model tabs — only the welcome/setup page.

---

### Part C: Configure Data Cloud — Data Ingestion (~15 min)

#### Step 5: Create the Contact Data Stream

1. Open the **Data Cloud** app (App Launcher → Data Cloud)
2. Click the **Data Streams** tab
3. Click **New** (top right)
4. Select **Salesforce CRM** as the source connector → click **Next**
5. From the list of available objects, find and select **Contact** (left sidebar)
6. You'll see the **Contact Details** configuration page:
   - Data Lake Object Label: `Contact_Home` (leave as default)
   - Data Lake Object API Name: `Contact_Home` (leave as default)
   - Data Stream Name: `Contact_Home` (leave as default)
   - Object Category: **Profile**
   - Primary Key: `Contact ID` (leave as default)
7. **Reduce the field selection** — by default all 69+ standard fields are selected. We only need a handful:
   - Uncheck the top-level checkbox to deselect all standard fields
   - Re-check ONLY these fields: `Contact ID`, `Email`, `FirstName`, `LastName`
   - Click the **Custom Fields** tab (next to "Standard Fields")
   - Check: `Loyalty_Tier__c`, `Churn_Risk__c`
8. Click **Next**
9. On the final review page, click **Deploy**
10. **Wait** for the initial ingestion to complete — the status will change from "Processing" to a green checkmark. This typically takes 2-5 minutes.

> **Timing note**: In Developer Edition orgs, ingestion is asynchronous and can take up to 10 minutes. If the data stream shows 0 records after 10 minutes, click the refresh icon or navigate away and back.

> **Why limit fields?** Ingesting all 69 standard fields creates noise in the Data Model and slows ingestion. We only need identity fields (Id, Email, Name) and our custom context fields (Loyalty Tier, Churn Risk).

---

### Part D: Configure Data Cloud — Data Model Mapping (~25 min)

This is the most critical and error-prone step. Data Cloud requires explicit mapping from your ingested data (Data Lake Object / DLO) to standardized Data Model Objects (DMOs). Identity Resolution will NOT work until this is done correctly.

The mapping UI is a visual canvas:
- **Left panel**: Your ingested source fields from Contact_Home
- **Right panel**: Target Data Model entities (DMOs) — initially empty until you select objects
- **Center**: Connection lines between mapped fields

#### Step 6: Open the Mapping Canvas and Select Target Objects

1. In Data Cloud, navigate to **Data Lake Objects** (via the Data Lake Objects dropdown in the top nav)
2. Click on **Contact_Home**
3. You will see the mapping canvas with your source fields on the left and "Data Model entities" on the right
4. The right panel initially says **"No objects selected"** with a **Select Objects** button
5. Click **Select Objects**
6. Search for and select **Individual** — click to add it
7. Search for and select **Contact Point Email** — click to add it
8. Confirm/close the object selector

You should now see both **Contact Point Email** and **Individual** in the right panel, each with their own fields listed.

#### Step 7: Map Fields to Individual DMO

Connect source fields to target fields by clicking the connector dot (⊙) on a source field and dragging to the corresponding target field:

9. Connect **Contact ID** (left, marked "Primary Key") → **Individual Id** (right, marked "Primary Key")
10. Connect **First Name** (left) → **First Name** (right, under Individual)
11. Connect **Last Name** (left) → **Last Name** (right, under Individual)

#### Step 8: Map Fields to Contact Point Email DMO

> **This step is mandatory.** Data Cloud will NOT allow Identity Resolution on Individual unless Contact Point Email is also mapped. Without this, Identity Resolution will block with: "Mappings from Data Streams to the standard Cloud Information Model objects such as Individual and Contact Points are required."

12. Connect **Contact ID** (left) → **Contact Point Email Id** (right, marked "Primary Key" under Contact Point Email)
13. Connect **Email** (left) → **Email Address** (right, under Contact Point Email)
14. Connect **Contact ID** (left) → **Party** (right, under Contact Point Email)

> **Critical**: The `Party` field MUST map to **Contact ID** — the same source field that maps to Individual Id. This is what links the email record to the person. Do NOT map Email to Party — that is the most common mistake and will break Identity Resolution silently.

15. Click **Save** (top right)

#### Step 9: Add Custom Fields to Individual DMO

Your custom fields (Loyalty Tier, Churn Risk) don't exist on the standard Individual DMO yet. You must save the initial mapping before you can add new fields.

16. Under the **Individual** section on the right panel, scroll down past the Unmapped fields and click **"Add New Field"**
17. An **"Add New Attribute"** dialog appears:
    - Field Label: `LoyaltyTier`
    - Field API Name: `LoyaltyTier` (**type this exactly — do NOT use underscores**)
    - Data Type: **Text**
    - Leave "Enable Value Suggestion" unchecked
    - Click **Save**
18. The new field appears under Individual. Connect **Loyalty Tier** (left) → **LoyaltyTier** (right, under Individual)
19. Click **"Add New Field"** again under Individual
20. In the "Add New Attribute" dialog:
    - Field Label: `ChurnRisk`
    - Field API Name: `ChurnRisk` (**type this exactly — do NOT use underscores**)
    - Data Type: **Text**
    - Click **Save**
21. Connect **Churn Risk** (left) → **ChurnRisk** (right, under Individual)

> **Critical**: The API names `LoyaltyTier` and `ChurnRisk` (no underscores) are what the MuleSoft `data-cloud-sapi` queries as `LoyaltyTier__c` and `ChurnRisk__c`. If you use underscored names (`Loyalty_Tier`, `Churn_Risk`), the Data Cloud query will return null for these fields and the agent will see every customer as UNKNOWN tier.
22. Click **Save** (top right of the mapping canvas)

#### Step 10: Refresh the Data Stream

After saving your mappings, you need to trigger a refresh so the data flows through the new mappings into the DMOs.

23. Navigate back to the **Contact_Home** data stream (Data Streams tab → click Contact_Home)
24. You'll see the data stream detail page showing: Stream Type: Ingest, Data Stream Status: Active, Total Records (e.g., 21)
25. Click **Refresh Now** (top right, next to Follow)
26. A dialog appears with two options:
    - Incremental Refresh — insert new and refresh existing data
    - **Full Refresh** — delete existing data and insert new data
27. Select **Full Refresh** and click **Refresh Now**
28. Wait for the refresh to complete — Last Run Status will show **Success** and Last Processed Records will update from 0 to your record count
27. On the right side, verify **Data Mapping** shows "Fields mapped: 9/15" (or similar) with status **READY**

> **Why refresh?** The initial deploy ingested data before your mappings existed. The refresh pushes the data through your new DMO mappings so Individual and Contact Point Email records get populated. Without this, Identity Resolution will see 0 Source Profiles.

#### Step 10 (cont.): Verify Mapping Completeness

Before proceeding, confirm your mapping canvas shows:

**Contact Point Email** — Is Mapped (3):
- [ ] Contact Point Email Id ← Contact ID
- [ ] Email Address ← Email
- [ ] Party ← Contact ID

**Individual** — Is Mapped (5):
- [ ] Individual Id ← Contact ID
- [ ] First Name ← First Name
- [ ] Last Name ← Last Name
- [ ] LoyaltyTier (custom) ← Loyalty Tier
- [ ] ChurnRisk (custom) ← Churn Risk

The canvas should show connection lines from the left panel fields to the right panel fields. If "Is Mapped" counts don't match, check for missing connections.

---

### Part E: Configure Data Cloud — Identity Resolution (~20 min)

#### Step 11: Create the Identity Resolution Ruleset

1. In Data Cloud, click the **Identity Resolutions** tab
2. The page will be empty — "0 items" (this is normal for a fresh org)
3. Click **New** (top right)
4. A "New Ruleset" dialog appears with two options:
   - **Create New Ruleset** — "Create a new identity resolution ruleset."
   - Install from Datakits — "Create a ruleset from an installed datakit."
5. Select **Create New Ruleset** and click **Next**
6. On the next page:
   - Primary Data Model Object: select **Individual**
   - Ruleset Name: `Golden User Resolution`
7. Click **Save**

> If "Individual" does not appear in the dropdown, go back to Part D and verify that Contact Point Email DMO is mapped with the Party field correctly. Data Cloud requires at least one contact point mapped before it enables identity resolution.

#### Step 12: Configure Match Rules

6. Click the **Match Rules** tab within your ruleset
7. Click **New Match Rule**
8. The "Add Match Rules" page shows default match rules and a Custom Rule option:
   - Fuzzy Name and Normalized Email ✓
   - Fuzzy Name and Normalized Phone ⚠️
   - Fuzzy Name and Normalized Address ⚠️
   - Fuzzy Name and Normalized Phone and Normalized Email ⚠️
   - **Custom Rule** ✓
9. Select **Custom Rule** and click **Next**
10. The custom rule configuration page appears:
    - Match Rule Name: `Custom Rule` (leave as default or rename to `Exact Email`)
    - **Match Criteria** table with columns: Data Model Object, Field, Match Method, Advanced Settings
11. The first row is pre-populated. Configure it:
    - Data Model Object: **Contact Point Email**
    - Field: **Email Address**
    - Match Method: **Exact**
12. A second row may appear for Individual. **Delete it** (click the trash icon 🗑️) — we only need the email match criterion.
13. Click **Save** (or **Next** if there are more steps)

> **Why only email?** The default rules use "Fuzzy Name" matching which could produce false positives in a training environment. Exact email is sufficient because each student/contact has a unique email address. The ⚠️ icons on other default rules indicate those require fields (phone, address) we haven't mapped.

> You may see a warning: "To improve unified profiles, add more match rule criteria." — **Ignore this.** For training purposes, exact email matching is sufficient and keeps the agent's lookups unambiguous.

#### Step 13: Configure Reconciliation Rules

10. Click the **Reconciliation Rules** tab
11. Find **Individual Id** in the list and click to edit it
12. The "Edit Reconciliation Rule for Individual Id" dialog appears:
    - Default Reconciliation Rule: toggle to **Disabled**
    - Field Reconciliation Rule: select **Source Priority** (the two options are "Most Frequent" and "Source Priority")
    - Ignore Empty Values: leave checked ✓
    - Data Lake Object: shows `Contact_Home` (leave as-is)
    - Click **Save**
13. Find **LoyaltyTier** → click to edit → set Field Reconciliation Rule to **Most Frequent** → click **Save**
14. Find **ChurnRisk** → click to edit → set Field Reconciliation Rule to **Most Frequent** → click **Save**

> **The Individual Id reconciliation rule is critical.** It defaults to "Source Priority" which is correct for our single-source setup. If you leave the Default Reconciliation Rule enabled without configuring it, you'll get a hard warning that blocks processing.

#### Step 14: Run Identity Resolution

16. Click the **Run** button (top right of the ruleset page)
17. **Wait 10-15 minutes** — Data Cloud in Developer orgs is strictly asynchronous
18. Refresh the page periodically. You are looking for:
    - Source Profiles: > 0 (should match your Contact count)
    - Unified Profiles: > 0

> **If Source Profiles shows 0**: The data hasn't propagated from the Data Stream through the mappings into the DMOs yet. Wait another 10 minutes and click Run again. This is a timing issue, not a configuration error.

---

### Part F: Configure Service Cloud — The Action Layer (~15 min)

#### Why Service Cloud?

Data Cloud gives the agent **context** (who is this customer, what's their loyalty tier, what's their churn risk). Service Cloud gives the agent the ability to **take action** — create a case, issue a credit, log an interaction. The MuleSoft `service-cloud-mcp` app will invoke a Salesforce Autolaunched Flow to create refund cases.

We build this as a Flow (not Apex) because:
- Flows are declarative and visible to admins
- They can be invoked via the REST API at `/services/data/v62.0/actions/custom/flow/Agent_Issue_Refund_Case`
- No code deployment needed — just activate the flow

#### Step 15: Create the Autolaunched Flow (Manual — UI)

> **Prefer code deployment?** Skip to Step 15b below for the metadata XML you can deploy with `sf` CLI.

1. Navigate to **Setup** → Quick Find → search **"Flows"** → click **Flows**
2. Click **New Flow**
3. Select **Autolaunched Flow (No Trigger)** → click **Create**

#### Step 15a: Define Input Variables

Create four input variables. For each one: click **New Resource** (in the Toolbox panel on the left), select "Variable", and configure as follows:

**Variable 1:**
- API Name: `var_ContactEmail`
- Data Type: **Text**
- Check **Available for Input** ✓
- Click **Done**

**Variable 2:**
- API Name: `var_OrderNumber`
- Data Type: **Text**
- Check **Available for Input** ✓
- Click **Done**

**Variable 3:**
- API Name: `var_RefundAmount`
- Data Type: **Currency**
- Decimal Places: `2`
- Check **Available for Input** ✓
- Click **Done**

**Variable 4:**
- API Name: `var_Reason`
- Data Type: **Text**
- Check **Available for Input** ✓
- Click **Done**

#### Step 15b: Add "Get Records" Element — Look Up Contact

4. On the canvas, click the **+** icon after the Start element
5. Select **Get Records**
6. Configure:
   - Label: `Get Contact by Email`
   - Object: **Contact**
   - Condition Requirements: **All Conditions Are Met**
   - Filter: Field = `Email`, Operator = `Equals`, Value = `{!var_ContactEmail}`
   - How Many Records to Store: **Only the first record**
   - How to Store: **Automatically store all fields**
7. Click **Done**

#### Step 15c: Add "Create Records" Element — Create Case

8. Click the **+** icon after the Get Records element
9. Select **Create Records**
10. Configure:
    - Label: `Create Refund Case`
    - How Many Records: **One**
    - Object: **Case**
    - Set Field Values:
      | Field | Value |
      |-------|-------|
      | ContactId | `{!Get_Contact_by_Email.Id}` |
      | Subject | `Refund Processed for Order {!var_OrderNumber}` |
      | Description | `{!var_Reason} - Amount: {!var_RefundAmount}` |
      | Status | `New` |
      | Type | `Other` |
11. Click **Done**

> **Note on Type field**: The picklist value must exist. Standard orgs have: `Mechanical`, `Electrical`, `Electronic`, `Structural`, `Other`. Use `Other` unless you've added a custom `Refund` value. To add one: Setup → Object Manager → Case → Fields → Type → Edit picklist values.

#### Step 15d: Save and Activate

12. Click **Save**
    - Flow Label: `Agent Issue Refund Case`
    - Flow API Name: `Agent_Issue_Refund_Case` (auto-generated from label)
    - Click **Save**
13. Click **Activate**

#### Step 15e: Deploy via CLI (Alternative to Manual)

If you have the Salesforce CLI (`sf`) installed, you can deploy the flow as metadata instead of building it manually.

First, authenticate to the org:

```bash
sf org login web --instance-url https://orgfarm-4a581f5625-dev-ed.develop.my.salesforce.com --alias agentic-training
```

Then create the following file structure and deploy:

```
force-app/
  main/
    default/
      flows/
        Agent_Issue_Refund_Case.flow-meta.xml
```

**File: `Agent_Issue_Refund_Case.flow-meta.xml`**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Flow xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>62.0</apiVersion>
    <interviewLabel>Agent Issue Refund Case {!$Flow.CurrentDateTime}</interviewLabel>
    <label>Agent Issue Refund Case</label>
    <processType>AutoLaunchedFlow</processType>
    <status>Active</status>
    <start>
        <locationX>50</locationX>
        <locationY>0</locationY>
        <connector>
            <targetReference>Get_Contact_by_Email</targetReference>
        </connector>
    </start>
    <variables>
        <name>var_ContactEmail</name>
        <dataType>String</dataType>
        <isCollection>false</isCollection>
        <isInput>true</isInput>
        <isOutput>false</isOutput>
    </variables>
    <variables>
        <name>var_OrderNumber</name>
        <dataType>String</dataType>
        <isCollection>false</isCollection>
        <isInput>true</isInput>
        <isOutput>false</isOutput>
    </variables>
    <variables>
        <name>var_RefundAmount</name>
        <dataType>Currency</dataType>
        <isCollection>false</isCollection>
        <isInput>true</isInput>
        <isOutput>false</isOutput>
        <scale>2</scale>
    </variables>
    <variables>
        <name>var_Reason</name>
        <dataType>String</dataType>
        <isCollection>false</isCollection>
        <isInput>true</isInput>
        <isOutput>false</isOutput>
    </variables>
    <recordLookups>
        <name>Get_Contact_by_Email</name>
        <label>Get Contact by Email</label>
        <locationX>176</locationX>
        <locationY>134</locationY>
        <connector>
            <targetReference>Create_Refund_Case</targetReference>
        </connector>
        <filterLogic>and</filterLogic>
        <filters>
            <field>Email</field>
            <operator>EqualTo</operator>
            <value>
                <elementReference>var_ContactEmail</elementReference>
            </value>
        </filters>
        <getFirstRecordOnly>true</getFirstRecordOnly>
        <object>Contact</object>
        <storeOutputAutomatically>true</storeOutputAutomatically>
    </recordLookups>
    <recordCreates>
        <name>Create_Refund_Case</name>
        <label>Create Refund Case</label>
        <locationX>176</locationX>
        <locationY>268</locationY>
        <inputAssignments>
            <field>ContactId</field>
            <value>
                <elementReference>Get_Contact_by_Email.Id</elementReference>
            </value>
        </inputAssignments>
        <inputAssignments>
            <field>Subject</field>
            <value>
                <stringValue>Refund Processed for Order {!var_OrderNumber}</stringValue>
            </value>
        </inputAssignments>
        <inputAssignments>
            <field>Description</field>
            <value>
                <stringValue>{!var_Reason} - Amount: {!var_RefundAmount}</stringValue>
            </value>
        </inputAssignments>
        <inputAssignments>
            <field>Status</field>
            <value>
                <stringValue>New</stringValue>
            </value>
        </inputAssignments>
        <inputAssignments>
            <field>Type</field>
            <value>
                <stringValue>Other</stringValue>
            </value>
        </inputAssignments>
        <object>Case</object>
    </recordCreates>
</Flow>
```

Deploy:

```bash
sf project deploy start --source-dir force-app --target-org agentic-training
```

#### Step 15f: Test the Flow via API

Verify the flow is callable from the REST API (this is how MuleSoft will invoke it):

```bash
TOKEN="<your-access-token>"
INSTANCE="https://orgfarm-4a581f5625-dev-ed.develop.my.salesforce.com"

curl -s -X POST "$INSTANCE/services/data/v62.0/actions/custom/flow/Agent_Issue_Refund_Case" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": [{
      "var_ContactEmail": "student-slack-test@globaltech.com",
      "var_OrderNumber": "ORD-TEST-001",
      "var_RefundAmount": 45.00,
      "var_Reason": "Late delivery"
    }]
  }'
```

**Expected response** (200 OK):
```json
[{
  "actionName": "Agent_Issue_Refund_Case",
  "errors": null,
  "isSuccess": true,
  "outputValues": {}
}]
```

After running, verify in Salesforce:
- Navigate to **Cases** tab (App Launcher → Cases)
- A new Case should exist with:
  - Subject: "Refund Processed for Order ORD-TEST-001"
  - Description: "Late delivery - Amount: 45.00"
  - Contact: Sarah Chen
  - Status: New
  - Type: Other

---

### Part G: Configure API Access — Connected App (~15 min)

#### Why a Connected App?

MuleSoft (or any external system) needs a secure way to authenticate against this Salesforce org and call the Data Cloud Query API. A Connected App provides OAuth 2.0 credentials (Client ID + Client Secret) that authorize server-to-server access without requiring a user to interactively log in.

We use the **Client Credentials** grant type because:
- It's the modern enterprise pattern for server-to-server integrations
- No username/password or security token required
- No interactive login prompt — the MuleSoft app authenticates silently
- Password-based OAuth is blocked in many training/developer orgs

The Connected App needs specific OAuth scopes that grant access to Data Cloud's query and profile APIs.

#### Step 16: Create the Connected App

> If rebuilding from scratch (original org lost), follow all steps below. If the app already exists, skip to Step 17 to verify.

1. Navigate to **Setup** → Quick Find → **App Manager**
2. Click **New Connected App** (top right)
3. Fill in the basic information:
   - Connected App Name: `Data Cloud External`
   - API Name: `Data_Cloud_External` (auto-populated)
   - Contact Email: your admin email
4. Under **API (Enable OAuth Settings)**:
   - Check **Enable OAuth Settings**
   - Callback URL: `https://localhost:8081/callback` (required field but not used for Client Credentials flow — any valid HTTPS URL works here)
   - **Selected OAuth Scopes** — add these four:
     - `Manage user data via APIs (api)`
     - `Perform requests at any time (refresh_token, offline_access)`
     - `Manage Data Cloud profile data (cdp_profile_api)`
     - `Perform SQL queries on Data Cloud data (cdp_query_api)`
   - Check **Enable Client Credentials Flow**
5. Click **Save**
6. Click **Continue** on the confirmation dialog
7. Wait 2-10 minutes for the app to propagate, then click **Manage Consumer Details**
8. After verifying your identity, you'll see:
   - **Consumer Key** (this is your Client ID)
   - **Consumer Secret** (this is your Client Secret)
9. **Copy both values** and store them securely — you will need them for MuleSoft configuration

> **Important**: Consumer Secret is shown only once at creation time. If lost, you must regenerate it.

#### Step 17: Enable Client Credentials Flow and Configure Policies

Since Client Credentials flow has no interactive login, the Connected App needs to be explicitly enabled for it and assigned a "Run As" user context.

> **Note**: In recent Salesforce releases, Connected Apps are managed under **External Client App Manager** (not the legacy "Manage Connected Apps" page).

10. Navigate to **Setup** → Quick Find → search **"App M"** → click **External Client App Manager** (under External Client Apps)
11. Click on **Data Cloud External** in the list
12. Click **Edit** (or navigate to the **Policies** tab)
13. Under **OAuth Flows and External Client App Enhancements**:
    - Check **Enable Client Credentials Flow**
14. Under **App Authorization**:
    - Refresh Token Policy: **Refresh token is valid until revoked** (default)
    - IP Relaxation: **Relax IP restrictions**
15. Scroll down to the **Client Credentials Flow** section:
    - For the **Run As** field, click the magnifying glass and select your admin user (the same username you log in with)
16. Click **Save**

> **Why Run As matters**: The token issued by Client Credentials flow inherits this user's permissions. The user must have access to Data Cloud objects and the Contact records we created.

> **Why Relax IP restrictions?** MuleSoft's CloudHub workers use dynamic IPs. Without relaxing IP restrictions, token requests from CloudHub will be rejected.

---

### Part H: Verify End-to-End with API Calls (~10 min)

#### Step 18: Find Your My Domain URL

1. Navigate to **Setup** → Quick Find → **My Domain**
2. Copy the **Current My Domain URL** (e.g., `https://yourorg.my.salesforce.com`)

> **Critical**: Do NOT use `login.salesforce.com` or `test.salesforce.com` for token requests. These public auth servers don't recognize org-specific Connected Apps. Always use your My Domain URL.

#### Step 19: Obtain an Access Token

Using curl (or Postman):

```bash
curl -X POST "https://<YOUR-MY-DOMAIN>.my.salesforce.com/services/oauth2/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=<YOUR-CONSUMER-KEY>" \
  -d "client_secret=<YOUR-CONSUMER-SECRET>"
```

**Expected response** (200 OK):
```json
{
  "access_token": "00D...",
  "instance_url": "https://<your-instance>.my.salesforce.com",
  "token_type": "Bearer"
}
```

Save the `access_token` and `instance_url` for the next steps.

#### Step 20: Query Data Cloud — Step 1: Find the Party ID

```bash
curl -X POST "https://<INSTANCE_URL>/services/data/v62.0/ssot/query" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT ssot__PartyId__c FROM ssot__ContactPointEmail__dlm WHERE ssot__EmailAddress__c = '\''student-slack-test@globaltech.com'\''"
  }'
```

**Expected response**: A JSON object containing `ssot__PartyId__c` (this will be the Contact ID, e.g., `003gL00000fwf81QAA`)

#### Step 21: Query Data Cloud — Step 2: Get the Unified Individual Profile

```bash
curl -X POST "https://<INSTANCE_URL>/services/data/v62.0/ssot/query" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT ssot__Id__c, ssot__FirstName__c, ssot__LastName__c, LoyaltyTier__c, ChurnRisk__c FROM ssot__Individual__dlm WHERE ssot__Id__c = '\''<PARTY_ID_FROM_STEP_18>'\''"
  }'
```

**Expected response**:
```json
{
  "data": [{
    "ssot__Id__c": "003gL00000fwf81QAA",
    "ssot__FirstName__c": "Sarah",
    "ssot__LastName__c": "Chen",
    "LoyaltyTier__c": "Platinum",
    "ChurnRisk__c": "Low"
  }]
}
```

> **Note on table names**: If `ssot__Individual__dlm` returns a 404, the table may have a different name. Go to Data Cloud → Data Model → search "Individual" → copy the exact Object API Name. Wrap it in double quotes in your SQL: `FROM "Exact_API_Name__dlm"`. Data Cloud uses ANSI SQL which is case-sensitive on table/field names.

#### Step 22: Test Service Cloud — Flow Invocation

```bash
curl -s -X POST "https://<INSTANCE_URL>/services/data/v62.0/actions/custom/flow/Agent_Issue_Refund_Case" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": [{
      "var_ContactEmail": "student-slack-test@globaltech.com",
      "var_OrderNumber": "ORD-VERIFY-001",
      "var_RefundAmount": 25.00,
      "var_Reason": "Verification test"
    }]
  }'
```

**Expected**: `"isSuccess": true`

#### Step 23: Test Service Cloud — Direct SOQL Query

```bash
curl -s "https://<INSTANCE_URL>/services/data/v62.0/query?q=SELECT+Id,Email,Loyalty_Tier__c,Churn_Risk__c+FROM+Contact+WHERE+Email='student-slack-test@globaltech.com'" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

**Expected**: Returns Sarah Chen with `Loyalty_Tier__c: "Platinum"`, `Churn_Risk__c: "Low"`

> **Field name distinction**: The Contact object fields are `Loyalty_Tier__c`/`Churn_Risk__c` (Salesforce auto-names them from the label). The Individual DMO fields you created are `LoyaltyTier__c`/`ChurnRisk__c` (you set those API names explicitly). The `data-cloud-sapi` app queries the DMO, so it uses the underscore-free names.

#### Step 24: Test Service Cloud — Opportunity Access

```bash
curl -s "https://<INSTANCE_URL>/services/data/v62.0/query?q=SELECT+Id,Name,StageName+FROM+Opportunity+LIMIT+1" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

**Expected**: Returns at least one Opportunity record (confirms CRUD access for service-cloud-mcp)

> If any of these tests fail, do NOT proceed to the MuleSoft exercises. Fix the issue using the troubleshooting table below.

---

### Verification Checklist

Before proceeding to the next exercise, confirm ALL of the following pass:

**Salesforce Setup**
- [ ] Golden Contact exists: Sarah Chen, student-slack-test@globaltech.com, Platinum, Low risk
- [ ] Custom fields exist on Contact: `Loyalty_Tier__c`, `Churn_Risk__c`
- [ ] Data Cloud initialized (setup wizard completed)
- [ ] Data Stream deployed and shows records ingested (Total Records > 0)
- [ ] Individual DMO has custom fields mapped: `LoyaltyTier__c`, `ChurnRisk__c` (API names without underscores — these are what `data-cloud-sapi` queries)
- [ ] Contact Point Email DMO mapped correctly (Contact ID→Contact Point Email Id, Contact ID→Party, Email→Email Address)
- [ ] Identity Resolution has run and shows Unified Profiles > 0
- [ ] Flow `Agent_Issue_Refund_Case` is Active

**Connected App & Auth**
- [ ] Connected App has Client Credentials flow enabled
- [ ] Run As user assigned
- [ ] IP Relaxation set to "Relax IP restrictions"
- [ ] Token request via My Domain URL returns 200 OK with access_token

**Data Cloud API (what `data-cloud-sapi` will use)**
- [ ] Query 1: email → Party ID returns a result
- [ ] Query 2: Party ID → Individual profile returns Sarah Chen with Platinum/Low

**Service Cloud API (what `service-cloud-mcp` will use)**
- [ ] Flow invocation via REST API returns `isSuccess: true`
- [ ] Case created in Salesforce with correct Subject, Description, Contact
- [ ] Direct SOQL query of Contact returns custom fields
- [ ] Opportunity query returns results (confirms CRUD access)
- [ ] Opportunity update returns HTTP 204 (confirms write access)

---

### Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| "Data Cloud" not in App Launcher | Org doesn't have Data Cloud license | Provision a new org from https://www.salesforce.com/products/free-trial/developer/ |
| Data Cloud shows welcome page only | Data Cloud instance not initialized | Click "Get Started" in the setup wizard (Part B) |
| Identity Resolution dropdown empty | Contact Point Email DMO not mapped | Map Contact ID→Party on Contact Point Email (Part D, Step 8) |
| "0 Source Profiles" after running | Data hasn't propagated through DMO mappings | Click "Refresh Now" → Full Refresh on the data stream, wait 10-15 min, Run again |
| Reconciliation warning blocks Run | Individual Id reconciliation rule not set | Edit Individual Id → disable Default rule → set to "Source Priority" |
| Token request returns 401 | Using login.salesforce.com instead of My Domain | Use `https://<my-domain>.my.salesforce.com/services/oauth2/token` |
| Token request returns "invalid_client" | Client Credentials flow not enabled or Run As not set | Enable in External Client App Manager + assign Run As user |
| Token request returns "invalid_client_id" | App not yet propagated (takes 2-10 min after creation) | Wait and retry |
| Query returns 404 for table name | Table name is different in your org | Data Cloud → Data Model → search "Individual" → use exact Object API Name |
| Query returns empty for email lookup | Identity Resolution hasn't unified the profile yet | Wait and re-run Identity Resolution; verify Refresh Now was done |
| Custom fields not in query results | Fields not added/mapped to Individual DMO | Use "Add New Field" on Individual DMO (Part D, Step 9) |
| Flow invocation returns 404 | Flow not activated or wrong API name | Check Setup → Flows → verify Active status and API name matches exactly |
| Flow returns `isSuccess: false` | Contact not found by email (typo) | Verify Contact email matches exactly: `student-slack-test@globaltech.com` |
| IP restriction error on token | IP Relaxation not set to "Relax" | External Client App Manager → Edit Policies → set IP Relaxation to "Relax IP restrictions" |

---

### Instructor Notes

- This exercise only needs to be done **once** for the entire class. All students share this org.
- The Data Cloud queries are read-only for students — they cannot accidentally corrupt the shared data.
- If you need to reset: delete the Identity Resolution ruleset, delete the data stream, remove custom fields, and start over. Allow 30 min for re-ingestion.
- The two-step query pattern (email → Party ID → Individual profile) is exactly what the `data-cloud-sapi` MuleSoft app implements. Students will see this in the code.

---
