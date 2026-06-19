*** Settings ***
Resource    ../resources/common_keywords.resource
Resource    ../pom_pages/login_page/login_page.resource
Test Setup    Open Login Page    http://172.21.166.115/washtabui/login?data=undefined
Test Teardown    Close Browser Session

*** Test Cases ***
AUT-WT-LOGIN01: Successful login with valid username and password
    [Tags]    WT-LOGIN01    positive
    Verify Login Page Loaded
    Enter User Name    ${VALID_USERNAME}
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button
    Location Should Contain    /washtabui/home

AUT-WT-LOGIN02: Login fails with incorrect username and correct password
    [Tags]    WT-LOGIN02    negative
    Verify Login Page Loaded
    Enter User Name    wronguser
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Login Rejected
    Location Should Contain    /washtabui/login

AUT-WT-LOGIN03: Login fails with correct username and incorrect password
    [Tags]    WT-LOGIN03    negative
    Verify Login Page Loaded
    Enter User Name    ${VALID_USERNAME}
    Enter Password    WrongPassword123
    Click Sign In Button
    Verify Login Rejected
    Location Should Contain    /washtabui/login

AUT-WT-LOGIN04: Login fails when username and password fields are blank
    [Tags]    WT-LOGIN04    negative
    Verify Login Page Loaded
    Enter User Name    ${EMPTY}
    Enter Password    ${EMPTY}
    Click Sign In Button
    Verify Username Required Validation
    Verify Password Required Validation
    Location Should Contain    /washtabui/login

AUT-WT-LOGIN05: Login fails when username is blank and password is entered
    [Tags]    WT-LOGIN05    negative
    Verify Login Page Loaded
    Enter User Name    ${EMPTY}
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Username Required Validation
    Location Should Contain    /washtabui/login

AUT-WT-LOGIN06: Login fails when password is blank and username is entered
    [Tags]    WT-LOGIN06    negative
    Verify Login Page Loaded
    Enter User Name    ${VALID_USERNAME}
    Enter Password    ${EMPTY}
    Click Sign In Button
    Verify Password Required Validation
    Location Should Contain    /washtabui/login

AUT-WT-LOGIN07: Verify login page UI elements are visible
    [Tags]    WT-LOGIN07    positive
    Verify Login Page Loaded
    Element Should Be Visible    ${USER_NAME_TEXTBOX}
    Element Should Be Visible    ${PASSWORD_TEXTBOX}
    Element Should Be Visible    ${SIGN_IN_BUTTON}

AUT-WT-LOGIN08: Login using Enter key instead of clicking Login button
    [Tags]    WT-LOGIN08    edge
    Verify Login Page Loaded
    Enter User Name    ${VALID_USERNAME}
    Enter Password    ${VALID_PASSWORD}
    Press Keys    ${PASSWORD_TEXTBOX}    ENTER
    Location Should Contain    /washtabui/home
    Page Should Contain Element    ${HOME_BUTTON}

AUT-WT-LOGIN09: Login with leading and trailing spaces in username
    [Tags]    WT-LOGIN09    edge
    Verify Login Page Loaded
    Enter User Name    ${SPACE}${VALID_USERNAME}${SPACE}
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button
    Location Should Contain    /washtabui/home

AUT-WT-LOGIN10: Login with leading and trailing spaces in password
    [Tags]    WT-LOGIN10    edge
    Verify Login Page Loaded
    Enter User Name    ${VALID_USERNAME}
    Enter Password    ${SPACE}${VALID_PASSWORD}${SPACE}
    Click Sign In Button
    Verify Login Rejected
    Location Should Contain    /washtabui/login

AUT-WT-LOGIN11: Login attempt with extremely long username input
    [Tags]    WT-LOGIN11    edge
    Verify Login Page Loaded
    Enter User Name    aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Login Rejected
    Location Should Contain    /washtabui/login

AUT-WT-LOGIN12: Login attempt with extremely long password input
    [Tags]    WT-LOGIN12    edge
    Verify Login Page Loaded
    Enter User Name    ${VALID_USERNAME}
    Enter Password    aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
    Click Sign In Button
    Verify Login Rejected
    Location Should Contain    /washtabui/login

AUT-WT-LOGIN13: Login with special characters in username
    [Tags]    WT-LOGIN13    negative
    Verify Login Page Loaded
    Enter User Name    !@#$$%
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Login Rejected
    Location Should Contain    /washtabui/login

AUT-WT-LOGIN14: Repeated clicking of Login button during submission
    [Tags]    WT-LOGIN14    edge
    Verify Login Page Loaded
    Enter User Name    ${VALID_USERNAME}
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button
    Click Sign In Button
    Click Sign In Button
    Location Should Contain    /washtabui/home
    Page Should Contain Element    ${HOME_BUTTON}

AUT-WT-LOGIN15: Browser back navigation after successful login returns to authenticated home
    [Tags]    WT-LOGIN15    edge
    Verify Login Page Loaded
    Enter User Name    ${VALID_USERNAME}
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button
    Location Should Contain    /washtabui/home
    Page Should Contain Element    ${HOME_BUTTON}
    Go Back
    Click Home Button
    Location Should Contain    /washtabui/home
    Page Should Contain Element    ${HOME_BUTTON}
