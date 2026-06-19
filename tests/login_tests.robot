*** Settings ***
Resource    ../resources/common_keywords.resource
Resource    ../pom_pages/login_page/login_page.resource
Suite Setup    Open Browser Session
Suite Teardown    Close Browser Session
Test Setup    Open Login Page

*** Test Cases ***
AUT-WT-LOGIN01: Verify login page loads with correct URL and UI elements
    [Tags]    WT-LOGIN01    positive
    Verify Login Page Loaded

AUT-WT-LOGIN02: Verify username textbox is visible and accepts input
    [Tags]    WT-LOGIN02    positive
    Verify Login Page Loaded
    Enter Username    ${VALID_USERNAME}
    Wait For Element To Be Ready    ${USERNAME_TEXTBOX}

AUT-WT-LOGIN03: Verify password textbox is visible and masks characters
    [Tags]    WT-LOGIN03    positive
    Verify Login Page Loaded
    Enter Password    ${VALID_PASSWORD}
    Verify Password Field Is Masked

AUT-WT-LOGIN04: Verify SIGN IN button is visible and clickable
    [Tags]    WT-LOGIN04    positive
    Verify Login Page Loaded
    Click Sign In Button
    Verify Login Failed And Still On Login Page

AUT-WT-LOGIN05: Verify successful login with valid credentials
    [Tags]    WT-LOGIN05    positive
    Verify Login Page Loaded
    Login With Credentials    ${VALID_USERNAME}    ${VALID_PASSWORD}
    Verify Successful Login Redirect

AUT-WT-LOGIN06: Verify login fails with incorrect password
    [Tags]    WT-LOGIN06    negative
    Verify Login Page Loaded
    Login With Credentials    ${VALID_USERNAME}    ${INVALID_PASSWORD}
    Verify Login Failed And Still On Login Page

AUT-WT-LOGIN07: Verify login fails with invalid username
    [Tags]    WT-LOGIN07    negative
    Verify Login Page Loaded
    Login With Credentials    ${INVALID_USERNAME}    ${VALID_PASSWORD}
    Verify Login Failed And Still On Login Page

AUT-WT-LOGIN08: Verify login fails with both username and password invalid
    [Tags]    WT-LOGIN08    negative
    Verify Login Page Loaded
    Login With Credentials    ${INVALID_USERNAME}    ${INVALID_PASSWORD}
    Verify Login Failed And Still On Login Page

AUT-WT-LOGIN09: Verify login attempt with empty username and password
    [Tags]    WT-LOGIN09    negative
    Verify Login Page Loaded
    Enter Username    ${EMPTY}
    Enter Password    ${EMPTY}
    Click Sign In Button
    Verify Username Required Validation
    Verify Password Required Validation

AUT-WT-LOGIN10: Verify login attempt with username only
    [Tags]    WT-LOGIN10    negative
    Verify Login Page Loaded
    Enter Username    ${VALID_USERNAME}
    Enter Password    ${EMPTY}
    Click Sign In Button
    Verify Password Required Validation

AUT-WT-LOGIN11: Verify login attempt with password only
    [Tags]    WT-LOGIN11    negative
    Verify Login Page Loaded
    Enter Username    ${EMPTY}
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Username Required Validation

AUT-WT-LOGIN12: Verify navigation using home navigation button
    [Tags]    WT-LOGIN12    positive
    Verify Login Page Loaded
    Click Home Navigation Button
    Verify Successful Login Redirect

AUT-WT-LOGIN13: Verify navigation using back navigation button
    [Tags]    WT-LOGIN13    positive
    Verify Login Page Loaded
    Click Back Navigation Button
    Verify Successful Login Redirect

AUT-WT-LOGIN14: Verify login with leading and trailing whitespace in username
    [Tags]    WT-LOGIN14    edge
    Verify Login Page Loaded
    Login With Credentials    ${SPACE}${VALID_USERNAME}${SPACE}    ${VALID_PASSWORD}
    Verify Login Failed And Still On Login Page

AUT-WT-LOGIN15: Verify login with very long username input
    [Tags]    WT-LOGIN15    edge
    Verify Login Page Loaded
    Login With Credentials    ${VALID_USERNAME}${VALID_USERNAME}${VALID_USERNAME}${VALID_USERNAME}${VALID_USERNAME}    ${VALID_PASSWORD}
    Verify Login Failed And Still On Login Page

AUT-WT-LOGIN16: Verify repeated clicking of SIGN IN button during login attempt
    [Tags]    WT-LOGIN16    edge
    Verify Login Page Loaded
    Enter Username    ${VALID_USERNAME}
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button
    Click Sign In Button
    Click Sign In Button
    Verify Successful Login Redirect

AUT-WT-LOGIN17: Verify login submission using Enter key
    [Tags]    WT-LOGIN17    edge
    Verify Login Page Loaded
    Enter Username    ${VALID_USERNAME}
    Enter Password    ${VALID_PASSWORD}
    Press Keys    ${PASSWORD_TEXTBOX}    ENTER
    Verify Successful Login Redirect

AUT-WT-LOGIN18: Verify login using pasted credentials
    [Tags]    WT-LOGIN18    edge
    Verify Login Page Loaded
    Login With Credentials    ${VALID_USERNAME}    ${VALID_PASSWORD}
    Verify Successful Login Redirect

AUT-WT-LOGIN19: Verify username case sensitivity during login
    [Tags]    WT-LOGIN19    edge
    Verify Login Page Loaded
    Login With Credentials    HACKLARR    ${VALID_PASSWORD}
    Verify Login Failed And Still On Login Page
