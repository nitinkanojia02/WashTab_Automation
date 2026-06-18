*** Settings ***
Resource    ../resources/common_keywords.resource
Resource    ../pom_pages/login_page/login_page.resource
Test Teardown    Close Browser Session

*** Test Cases ***
AUT-WT-LOGIN01: Verify login page loads successfully
    [Tags]    WT-LOGIN01    positive
    Open Login Page    ${LOGIN_PAGE_URL}
    Verify Login Page Loaded

AUT-WT-LOGIN02: Login with valid username and valid password
    [Tags]    WT-LOGIN02    positive
    Open Login Page    ${LOGIN_PAGE_URL}
    Verify Login Page Loaded
    Enter Username    ${VALID_USERNAME}
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button

AUT-WT-LOGIN03: Verify login failure with incorrect username and valid password
    [Tags]    WT-LOGIN03    negative
    Open Login Page    ${LOGIN_PAGE_URL}
    Verify Login Page Loaded
    Enter Username    ${INVALID_USERNAME}
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Login Rejected

AUT-WT-LOGIN04: Verify login failure with valid username and incorrect password
    [Tags]    WT-LOGIN04    negative
    Open Login Page    ${LOGIN_PAGE_URL}
    Verify Login Page Loaded
    Enter Username    ${VALID_USERNAME}
    Enter Password    ${INVALID_PASSWORD}
    Click Sign In Button
    Verify Login Rejected

AUT-WT-LOGIN05: Verify login failure with both username and password incorrect
    [Tags]    WT-LOGIN05    negative
    Open Login Page    ${LOGIN_PAGE_URL}
    Verify Login Page Loaded
    Enter Username    ${INVALID_USERNAME}
    Enter Password    ${INVALID_PASSWORD}
    Click Sign In Button
    Verify Login Rejected

AUT-WT-LOGIN06: Verify login failure when username and password fields are blank
    [Tags]    WT-LOGIN06    negative
    Open Login Page    ${LOGIN_PAGE_URL}
    Verify Login Page Loaded
    Enter Username    ${EMPTY}
    Enter Password    ${EMPTY}
    Click Sign In Button
    Verify Login Rejected

AUT-WT-LOGIN07: Verify login failure when username is blank and password is entered
    [Tags]    WT-LOGIN07    negative
    Open Login Page    ${LOGIN_PAGE_URL}
    Verify Login Page Loaded
    Enter Username    ${EMPTY}
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Username Required Validation

AUT-WT-LOGIN08: Verify login failure when password is blank and username is entered
    [Tags]    WT-LOGIN08    negative
    Open Login Page    ${LOGIN_PAGE_URL}
    Verify Login Page Loaded
    Enter Username    ${VALID_USERNAME}
    Enter Password    ${EMPTY}
    Click Sign In Button
    Verify Password Required Validation

AUT-WT-LOGIN09: Verify username field accepts leading and trailing spaces
    [Tags]    WT-LOGIN09    edge
    Open Login Page    ${LOGIN_PAGE_URL}
    Verify Login Page Loaded
    Enter Username    ${SPACE}${VALID_USERNAME}${SPACE}
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Login Rejected

AUT-WT-LOGIN10: Verify password field with leading and trailing spaces
    [Tags]    WT-LOGIN10    edge
    Open Login Page    ${LOGIN_PAGE_URL}
    Verify Login Page Loaded
    Enter Username    ${VALID_USERNAME}
    Enter Password    ${SPACE}${VALID_PASSWORD}${SPACE}
    Click Sign In Button
    Verify Login Rejected

AUT-WT-LOGIN11: Verify login behavior with very long username input
    [Tags]    WT-LOGIN11    edge
    Open Login Page    ${LOGIN_PAGE_URL}
    Verify Login Page Loaded
    Enter Username    ${VALID_USERNAME}${VALID_USERNAME}${VALID_USERNAME}${VALID_USERNAME}${VALID_USERNAME}${VALID_USERNAME}
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Login Rejected

AUT-WT-LOGIN12: Verify login behavior with very long password input
    [Tags]    WT-LOGIN12    edge
    Open Login Page    ${LOGIN_PAGE_URL}
    Verify Login Page Loaded
    Enter Username    ${VALID_USERNAME}
    Enter Password    ${VALID_PASSWORD}${VALID_PASSWORD}${VALID_PASSWORD}${VALID_PASSWORD}${VALID_PASSWORD}
    Click Sign In Button
    Verify Login Rejected

AUT-WT-LOGIN13: Verify username field with special characters
    [Tags]    WT-LOGIN13    negative
    Open Login Page    ${LOGIN_PAGE_URL}
    Verify Login Page Loaded
    Enter Username    !@#$%^&*()
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Login Rejected

AUT-WT-LOGIN14: Verify password field accepts special characters
    [Tags]    WT-LOGIN14    edge
    Open Login Page    ${LOGIN_PAGE_URL}
    Verify Login Page Loaded
    Enter Username    ${VALID_USERNAME}
    Enter Password    ${VALID_PASSWORD}!@#
    Click Sign In Button
    Verify Login Rejected

AUT-WT-LOGIN15: Verify case sensitivity of username
    [Tags]    WT-LOGIN15    edge
    Open Login Page    ${LOGIN_PAGE_URL}
    Verify Login Page Loaded
    Enter Username    HAKLARR
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Login Rejected

AUT-WT-LOGIN16: Verify case sensitivity of password
    [Tags]    WT-LOGIN16    negative
    Open Login Page    ${LOGIN_PAGE_URL}
    Verify Login Page Loaded
    Enter Username    ${VALID_USERNAME}
    Enter Password    icstunnel1
    Click Sign In Button
    Verify Login Rejected

AUT-WT-LOGIN17: Verify login submission using keyboard Enter key
    [Tags]    WT-LOGIN17    edge
    Open Login Page    ${LOGIN_PAGE_URL}
    Verify Login Page Loaded
    Enter Username    ${VALID_USERNAME}
    Enter Password    ${VALID_PASSWORD}
    Submit Login With Enter Key

AUT-WT-LOGIN18: Verify behavior when Login button is clicked multiple times quickly
    [Tags]    WT-LOGIN18    edge
    Open Login Page    ${LOGIN_PAGE_URL}
    Verify Login Page Loaded
    Enter Username    ${VALID_USERNAME}
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button
    Click Sign In Button
