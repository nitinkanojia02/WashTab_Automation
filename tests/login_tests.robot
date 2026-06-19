*** Settings ***
Resource    ../resources/common_keywords.resource
Resource    ../pom_pages/login_page/login_page.resource
Test Setup    Open Login Page    http://172.21.166.115/washtabui/login?data=undefined
Test Teardown    Close Browser Session

*** Test Cases ***
AUT-WT-LOGIN01: Verify login page loads with correct URL and login form is visible
    [Tags]    WT-LOGIN01    positive
    Verify Login Page Loaded

AUT-WT-LOGIN02: Verify username textbox accepts input
    [Tags]    WT-LOGIN02    positive
    Verify Login Page Loaded
    Enter Username    ${VALID_USERNAME}
    Element Attribute Value Should Be    ${USERNAME_TEXTBOX}    value    ${VALID_USERNAME}

AUT-WT-LOGIN03: Verify password textbox masks entered characters
    [Tags]    WT-LOGIN03    positive
    Verify Login Page Loaded
    Enter Password    ${VALID_PASSWORD}
    Verify Password Field Is Masked

AUT-WT-LOGIN04: Verify successful login with valid credentials
    [Tags]    WT-LOGIN04    positive
    Verify Login Page Loaded
    Enter Username    ${VALID_USERNAME}
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Successful Login Redirect

AUT-WT-LOGIN05: Verify login fails with invalid username and valid password
    [Tags]    WT-LOGIN05    negative
    Verify Login Page Loaded
    Enter Username    ${INVALID_USERNAME}
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Login Rejected

AUT-WT-LOGIN06: Verify login fails with valid username and invalid password
    [Tags]    WT-LOGIN06    negative
    Verify Login Page Loaded
    Enter Username    ${VALID_USERNAME}
    Enter Password    ${INVALID_PASSWORD}
    Click Sign In Button
    Verify Login Rejected

AUT-WT-LOGIN07: Verify login fails when both username and password are invalid
    [Tags]    WT-LOGIN07    negative
    Verify Login Page Loaded
    Enter Username    ${INVALID_USERNAME}
    Enter Password    ${INVALID_PASSWORD}
    Click Sign In Button
    Verify Login Rejected

AUT-WT-LOGIN08: Verify login fails when username and password fields are empty
    [Tags]    WT-LOGIN08    negative
    Verify Login Page Loaded
    Enter Username    ${EMPTY}
    Enter Password    ${EMPTY}
    Click Sign In Button
    Verify Login Rejected

AUT-WT-LOGIN09: Verify login fails when username is empty and password is provided
    [Tags]    WT-LOGIN09    negative
    Verify Login Page Loaded
    Enter Username    ${EMPTY}
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Username Required Validation

AUT-WT-LOGIN10: Verify login fails when password is empty and username is provided
    [Tags]    WT-LOGIN10    negative
    Verify Login Page Loaded
    Enter Username    ${VALID_USERNAME}
    Enter Password    ${EMPTY}
    Click Sign In Button
    Verify Password Required Validation

AUT-WT-LOGIN11: Verify back navigation button redirects user to home page
    [Tags]    WT-LOGIN11    positive
    Verify Login Page Loaded
    Click Back Navigation Button
    Wait Until Location Contains    ${HOME_PATH_FRAGMENT}    10s

AUT-WT-LOGIN12: Verify home navigation button redirects user to home page
    [Tags]    WT-LOGIN12    positive
    Verify Login Page Loaded
    Click Home Navigation Button
    Wait Until Location Contains    ${HOME_PATH_FRAGMENT}    10s

AUT-WT-LOGIN13: Verify login behavior with leading and trailing spaces in credentials
    [Tags]    WT-LOGIN13    edge
    Verify Login Page Loaded
    Enter Username    ${SPACE}${VALID_USERNAME}${SPACE}
    Enter Password    ${SPACE}${VALID_PASSWORD}${SPACE}
    Click Sign In Button
    ${status}    ${msg}=    Run Keyword And Ignore Error    Verify Successful Login Redirect
    Run Keyword If    '${status}' == 'FAIL'    Verify Login Rejected

AUT-WT-LOGIN14: Verify login fails with extremely long username and password values
    [Tags]    WT-LOGIN14    edge
    Verify Login Page Loaded
    ${LONG}=    Evaluate    "a"*210
    Enter Username    ${LONG}
    Enter Password    ${LONG}
    Click Sign In Button
    Verify Login Rejected

AUT-WT-LOGIN15: Verify system handles multiple rapid clicks on SIGN IN button
    [Tags]    WT-LOGIN15    edge
    Verify Login Page Loaded
    Enter Username    ${VALID_USERNAME}
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button
    Click Sign In Button
    Click Sign In Button
    Verify Successful Login Redirect

AUT-WT-LOGIN16: Verify login fails when username and password contain only whitespace
    [Tags]    WT-LOGIN16    negative
    Verify Login Page Loaded
    Enter Username    ${SPACE}
    Enter Password    ${SPACE}
    Click Sign In Button
    Verify Login Rejected

AUT-WT-LOGIN17: Verify login submission using Enter key with valid credentials
    [Tags]    WT-LOGIN17    edge
    Verify Login Page Loaded
    Enter Username    ${VALID_USERNAME}
    Enter Password    ${VALID_PASSWORD}
    Press Keys    ${PASSWORD_TEXTBOX}    ENTER
    Verify Successful Login Redirect

AUT-WT-LOGIN18: Verify login fails with special characters in username and password
    [Tags]    WT-LOGIN18    negative
    Verify Login Page Loaded
    Enter Username    !@#$$%
    Enter Password    !@#$$%
    Click Sign In Button
    Verify Login Rejected
