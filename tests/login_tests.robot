*** Settings ***
Resource    ../resources/common_keywords.resource
Resource    ../pom_pages/login_page/login_page.resource
Test Setup    Open Login Page    ${LOGIN_PAGE_URL}
Test Teardown    Close Browser Session

*** Test Cases ***
AUT-WT-LOGIN01: Verify login page loads with username textbox, password textbox, SIGN IN button, home navigation button and back navigation button visible
    [Tags]    WT-LOGIN01    positive
    Verify Login Page Loaded

AUT-WT-LOGIN02: Verify successful login using valid username and valid password through SIGN IN button
    [Tags]    WT-LOGIN02    positive
    Verify Login Page Loaded
    Enter Username    ${VALID_USERNAME}
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Successful Login Redirect

AUT-WT-LOGIN03: Verify login submission using Enter key from password textbox with valid credentials
    [Tags]    WT-LOGIN03    edge
    Verify Login Page Loaded
    Enter Username    ${VALID_USERNAME}
    Enter Password    ${VALID_PASSWORD}
    Submit Login With Enter Key
    Verify Successful Login Redirect

AUT-WT-LOGIN04: Verify login fails when valid username is used with incorrect password
    [Tags]    WT-LOGIN04    negative
    Verify Login Page Loaded
    Enter Username    ${VALID_USERNAME}
    Enter Password    ${INVALID_PASSWORD}
    Click Sign In Button
    Verify Login Failed And Still On Login Page

AUT-WT-LOGIN05: Verify login fails when invalid username is used with valid password
    [Tags]    WT-LOGIN05    negative
    Verify Login Page Loaded
    Enter Username    ${INVALID_USERNAME}
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Login Failed And Still On Login Page

AUT-WT-LOGIN06: Verify login fails when both username and password are invalid
    [Tags]    WT-LOGIN06    negative
    Verify Login Page Loaded
    Enter Username    ${INVALID_USERNAME}
    Enter Password    ${INVALID_PASSWORD}
    Click Sign In Button
    Verify Login Failed And Still On Login Page

AUT-WT-LOGIN07: Verify login validation when both username and password fields are empty
    [Tags]    WT-LOGIN07    negative
    Verify Login Page Loaded
    Enter Username    ${EMPTY}
    Enter Password    ${EMPTY}
    Click Sign In Button
    Verify Username Required Validation
    Verify Password Required Validation

AUT-WT-LOGIN08: Verify login validation when username is entered and password field is empty
    [Tags]    WT-LOGIN08    negative
    Verify Login Page Loaded
    Enter Username    ${VALID_USERNAME}
    Enter Password    ${EMPTY}
    Click Sign In Button
    Verify Password Required Validation

AUT-WT-LOGIN09: Verify login validation when password is entered and username field is empty
    [Tags]    WT-LOGIN09    negative
    Verify Login Page Loaded
    Enter Username    ${EMPTY}
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Username Required Validation

AUT-WT-LOGIN10: Verify password textbox masks characters while user types password
    [Tags]    WT-LOGIN10    positive
    Verify Login Page Loaded
    Enter Password    ${VALID_PASSWORD}
    Verify Password Field Is Masked

AUT-WT-LOGIN11: Verify login succeeds when valid credentials are entered with leading and trailing spaces
    [Tags]    WT-LOGIN11    edge
    Verify Login Page Loaded
    Enter Username    ${SPACE}${VALID_USERNAME}${SPACE}
    Enter Password    ${SPACE}${VALID_PASSWORD}${SPACE}
    Click Sign In Button
    Verify Successful Login Redirect

AUT-WT-LOGIN12: Verify login fails when username and password contain only whitespace characters
    [Tags]    WT-LOGIN12    negative
    Verify Login Page Loaded
    Enter Username    ${SPACE}${SPACE}
    Enter Password    ${SPACE}${SPACE}
    Click Sign In Button
    Verify Login Failed And Still On Login Page

AUT-WT-LOGIN13: Verify login using copy and paste actions for username and password fields
    [Tags]    WT-LOGIN13    edge
    Verify Login Page Loaded
    Enter Username    ${VALID_USERNAME}
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Successful Login Redirect

AUT-WT-LOGIN14: Verify system behavior when SIGN IN button is clicked repeatedly during login submission
    [Tags]    WT-LOGIN14    edge
    Verify Login Page Loaded
    Enter Username    ${VALID_USERNAME}
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button
    Click Sign In Button
    Click Sign In Button
    Verify Successful Login Redirect

AUT-WT-LOGIN15: Verify navigation to home page using home navigation button from login page
    [Tags]    WT-LOGIN15    positive
    Verify Login Page Loaded
    Click Home Navigation Button
    Verify Home Navigation Redirects To Home Page

AUT-WT-LOGIN16: Verify navigation to home page using back navigation button from login page
    [Tags]    WT-LOGIN16    positive
    Verify Login Page Loaded
    Click Back Navigation Button
    Verify Back Navigation Redirects To Home Page

AUT-WT-LOGIN17: Verify login behavior when extremely long username and password values are entered
    [Tags]    WT-LOGIN17    edge
    Verify Login Page Loaded
    ${long}=    Evaluate    "A"*210
    Enter Username    ${long}
    Enter Password    ${long}
    Click Sign In Button
    Verify Login Failed And Still On Login Page

AUT-WT-LOGIN18: Verify login fails when username case differs from the valid credential case
    [Tags]    WT-LOGIN18    negative
    Verify Login Page Loaded
    Enter Username    HACKLARR
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Login Failed And Still On Login Page
